"""
Framework-independent recommendation service.

This module is a thin, cached wrapper around the project's existing
recommendation code. It contains NO recommendation algorithms of its own:

    content  -> models.content_based.recommend_similar_items
    cf       -> models.collaborative_filtering.build_item_cf_model
                + get_similar_items
    hybrid   -> item-CF candidates + content candidates, fused with
                models.hybrid.build_hybrid_recommendations (weighted RRF)

It can be reused by any interface (FastAPI, an MCP server, a CLI, ...):

    from src.recommender_service import get_service

    service = get_service()
    service.search("movies", "batman")
    service.recommend("games", item_id, method="hybrid", top_n=10)

Design notes
------------
* Everything expensive (catalog, TF-IDF model, item-CF model) is built
  lazily, once per domain, and cached for the life of the process.
* Per-resource locks prevent two simultaneous requests from building the
  same model twice.
* A free-memory guard and MemoryError handling turn "too big for this
  machine" into a clean MethodUnavailableError instead of a crash.
* Scores from different methods mean different things, so every
  recommendation carries a `score_type` label. They are NOT probabilities.
"""

from __future__ import annotations

import gc
import logging
import math
import os
import sys
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

# Make the project root importable no matter where the process starts.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:  # optional: only used for the memory guard / status report
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

from src.config import (  # noqa: E402
    CF_N_NEIGHBORS,
    GAMES_META_FILE,
    GAMES_TRAIN_FILE,
    MOVIES_META_FILE,
    MOVIES_TRAIN_FILE,
)
from models.collaborative_filtering.collaborative_filtering import (  # noqa: E402
    build_item_cf_model,
    get_similar_items,
)
from models.content_based.content_based import (  # noqa: E402
    build_content_based_model,
    recommend_similar_items,
)
from models.hybrid.hybrid import build_hybrid_recommendations  # noqa: E402

logger = logging.getLogger("recomai.service")


# ============================================================
# Constants
# ============================================================

METHODS = ("content", "cf", "hybrid")

SCORE_TYPES = {
    "content": "tfidf_cosine_similarity",
    "cf": "item_cf_cosine_similarity",
    "hybrid": "weighted_rrf_score",
}

DEFAULT_TOP_N = 10
MAX_TOP_N = 50
DEFAULT_SEARCH_LIMIT = 8
MAX_SEARCH_LIMIT = 25
MIN_QUERY_LENGTH = 2

# Hybrid settings mirror the defaults of the existing hybrid module.
HYBRID_CANDIDATE_SIZE = 50
HYBRID_CF_WEIGHT = 0.5
HYBRID_CONTENT_WEIGHT = 0.5
HYBRID_RRF_K = 60

# After a failed build, do not retry for this many seconds.
FAILURE_COOLDOWN_SECONDS = 120

# Rough EXTRA free RAM (GB) needed on top of what the running process already
# uses, before attempting to build a resource.
# MEASURED (Games): the process peaked at ~0.46 GB in total (about 0.13 GB of
# that is the Python/sklearn baseline) with the catalog and both models loaded;
# each model added roughly 0.12 GB. MEASURED (Movies catalog): ~0.43 GB peak,
# i.e. ~0.3 GB above the baseline.
# Movies content/CF figures are EXTRAPOLATIONS, not measurements (about 4.5x the
# items and 8x the ratings of Games), with headroom. Treat them as conservative.
# Set RECOMMENDER_MEMORY_GUARD=0 to disable the check.
MEMORY_ESTIMATES_GB = {
    ("games", "catalog"): 0.2,
    ("games", "content"): 0.25,
    ("games", "cf"): 0.3,
    ("movies", "catalog"): 0.45,
    ("movies", "content"): 1.0,
    ("movies", "cf"): 1.8,
}


# ============================================================
# Errors
# ============================================================

class RecommenderServiceError(Exception):
    """Base class for service errors."""


class InvalidRequestError(RecommenderServiceError):
    """The request parameters are invalid."""


class ItemNotFoundError(RecommenderServiceError):
    """The requested item does not exist in this domain."""


class MethodUnavailableError(RecommenderServiceError):
    """A model could not be loaded (missing data, not enough memory...)."""


# ============================================================
# Domain configuration
# ============================================================

@dataclass(frozen=True)
class _Domain:
    key: str
    label: str
    meta_file: Path
    train_file: Path


DOMAINS = {
    "movies": _Domain("movies", "Movies & TV", MOVIES_META_FILE, MOVIES_TRAIN_FILE),
    "games": _Domain("games", "Video Games", GAMES_META_FILE, GAMES_TRAIN_FILE),
}


@dataclass
class _Catalog:
    """Slim, search-oriented view of a domain (never sent whole to clients)."""

    items: pd.DataFrame        # indexed by item_id: product_title, price, num_ratings
    titles_lc: np.ndarray      # lower-cased titles, row-aligned with `items`


# ============================================================
# Helpers
# ============================================================

def _clean_number(value: Any, digits: int | None = None) -> float | None:
    """Convert numpy/pandas numbers to JSON-safe floats (NaN -> None)."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits) if digits is not None else number


def _clean_int(value: Any) -> int | None:
    number = _clean_number(value)
    return None if number is None else int(number)


def _item_rating_counts(train_file: Path) -> pd.Series:
    """
    Count ratings per item reading ONLY the item_id column with pyarrow.
    Much lighter than loading the full training table into pandas.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    column = pq.read_table(train_file, columns=["item_id"]).column("item_id")
    counts = pc.value_counts(column)
    return pd.Series(
        counts.field("counts").to_numpy(),
        index=counts.field("values").to_pandas(),
    )


# ============================================================
# Service
# ============================================================

class RecommenderService:
    """Cached, lazily-initialised access to the recommendation models."""

    def __init__(self) -> None:
        self._cache: dict[tuple, Any] = {}
        self._build_seconds: dict[tuple, float] = {}
        self._failures: dict[tuple, tuple[float, str]] = {}
        self._locks: dict[tuple, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    # --------------------------------------------------------
    # Generic lazy-resource machinery
    # --------------------------------------------------------

    def _lock_for(self, key: tuple) -> threading.Lock:
        with self._registry_lock:
            return self._locks.setdefault(key, threading.Lock())

    @staticmethod
    def _check_memory(key: tuple, label: str) -> None:
        if psutil is None or os.getenv("RECOMMENDER_MEMORY_GUARD", "1") == "0":
            return
        needed = MEMORY_ESTIMATES_GB.get(key)
        if needed is None:
            return
        available = psutil.virtual_memory().available / 1024 ** 3
        if available < needed:
            raise MethodUnavailableError(
                f"Not enough free memory to load the {label}: it needs roughly "
                f"{needed:.1f} GB and only {available:.1f} GB is available. "
                f"Close other applications and try again, or choose another method."
            )

    def _resource(self, key: tuple, label: str, builder: Callable[[], Any]) -> Any:
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        with self._lock_for(key):
            cached = self._cache.get(key)
            if cached is not None:
                return cached

            failure = self._failures.get(key)
            if failure and time.time() - failure[0] < FAILURE_COOLDOWN_SECONDS:
                raise MethodUnavailableError(failure[1])

            self._check_memory(key, label)

            logger.info("Building %s ...", label)
            started = time.perf_counter()
            try:
                value = builder()
            except MemoryError:
                gc.collect()
                message = (
                    f"The {label} could not be built because the machine ran out "
                    f"of memory. Close other applications or choose another method."
                )
                self._failures[key] = (time.time(), message)
                logger.error(message)
                raise MethodUnavailableError(message) from None
            except FileNotFoundError as error:
                message = f"A data file required for the {label} was not found: {error.filename}"
                self._failures[key] = (time.time(), message)
                logger.error(message)
                raise MethodUnavailableError(message) from None

            elapsed = time.perf_counter() - started
            self._cache[key] = value
            self._build_seconds[key] = round(elapsed, 1)
            logger.info("Built %s in %.1fs", label, elapsed)
            return value

    # --------------------------------------------------------
    # Resource builders
    # --------------------------------------------------------

    def _catalog(self, domain: str) -> _Catalog:
        cfg = DOMAINS[domain]

        def build() -> _Catalog:
            meta = pd.read_parquet(
                cfg.meta_file, columns=["item_id", "product_title", "price"]
            )
            meta["product_title"] = meta["product_title"].astype(object)
            meta = meta[meta["product_title"].notna()]
            # Normalise whitespace (some titles contain non-breaking spaces)
            # so display and search behave consistently.
            meta["product_title"] = (
                meta["product_title"]
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
            meta = meta[meta["product_title"] != ""]
            meta = meta.drop_duplicates("item_id")

            counts = _item_rating_counts(cfg.train_file)
            meta["num_ratings"] = (
                meta["item_id"].map(counts).fillna(0).astype("int64")
            )
            # Only items that actually appear in the training ratings.
            meta = meta[meta["num_ratings"] > 0].set_index("item_id")

            titles_lc = meta["product_title"].str.lower().to_numpy(dtype=object)
            return _Catalog(items=meta, titles_lc=titles_lc)

        return self._resource(
            (domain, "catalog"), f"{cfg.label} catalog", build
        )

    def _content_model(self, domain: str) -> dict:
        cfg = DOMAINS[domain]

        def build() -> dict:
            metadata = pd.read_parquet(
                cfg.meta_file,
                columns=["item_id", "product_title", "description", "categories"],
            )
            # The existing model relies on row order == TF-IDF row order,
            # so make the index a clean 0..n-1 range with unique item ids.
            metadata = metadata.drop_duplicates("item_id").reset_index(drop=True)
            return build_content_based_model(metadata, max_features=5000)

        return self._resource(
            (domain, "content"), f"{cfg.label} content-based model", build
        )

    def _cf_model(self, domain: str) -> dict:
        cfg = DOMAINS[domain]

        def build() -> dict:
            train = pd.read_parquet(
                cfg.train_file, columns=["user_id", "item_id", "rating"]
            )
            model = build_item_cf_model(train, n_neighbors=CF_N_NEIGHBORS)
            del train
            # get_similar_items() only needs the NN model, the item-user
            # matrix and the item encoder. Drop the large encoded copy.
            model.pop("ratings_encoded", None)
            gc.collect()
            return model

        return self._resource(
            (domain, "cf"), f"{cfg.label} item-based CF model", build
        )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    @staticmethod
    def _validate_domain(domain: str) -> str:
        if domain not in DOMAINS:
            raise InvalidRequestError(
                f"Unknown domain '{domain}'. Use one of: {', '.join(DOMAINS)}."
            )
        return domain

    @staticmethod
    def _validate_method(method: str) -> str:
        if method not in METHODS:
            raise InvalidRequestError(
                f"Unknown method '{method}'. Use one of: {', '.join(METHODS)}."
            )
        return method

    @staticmethod
    def _validate_top_n(top_n: int) -> int:
        if not isinstance(top_n, (int, np.integer)) or not 1 <= top_n <= MAX_TOP_N:
            raise InvalidRequestError(f"top_n must be between 1 and {MAX_TOP_N}.")
        return int(top_n)

    # --------------------------------------------------------
    # Search / item lookup
    # --------------------------------------------------------

    def search(
        self, domain: str, query: str, limit: int = DEFAULT_SEARCH_LIMIT
    ) -> list[dict]:
        """
        Case-insensitive title search. Every word of the query must appear
        in the title. Titles that START with the query rank first, then
        more-rated (more popular) titles. Returns at most `limit` results.
        """
        domain = self._validate_domain(domain)
        text = (query or "").strip().lower()
        if len(text) < MIN_QUERY_LENGTH:
            raise InvalidRequestError(
                f"Search text must be at least {MIN_QUERY_LENGTH} characters."
            )
        limit = max(1, min(int(limit), MAX_SEARCH_LIMIT))

        catalog = self._catalog(domain)
        titles = pd.Series(catalog.titles_lc, copy=False)

        mask = np.ones(len(titles), dtype=bool)
        for token in text.split():
            mask &= titles.str.contains(token, regex=False, na=False).to_numpy()

        positions = np.flatnonzero(mask)
        if positions.size == 0:
            return []

        matched = catalog.items.iloc[positions]
        starts_with = titles.iloc[positions].str.startswith(text).to_numpy()
        popularity = matched["num_ratings"].to_numpy()

        # lexsort: last key is the primary key.
        order = np.lexsort((-popularity, ~starts_with))[:limit]
        top = matched.iloc[order]

        return [
            {
                "item_id": item_id,
                "product_title": row.product_title,
                "price": _clean_number(row.price, 2),
                "num_ratings": _clean_int(row.num_ratings),
            }
            for item_id, row in zip(top.index, top.itertuples())
        ]

    def get_item(self, domain: str, item_id: str) -> dict:
        domain = self._validate_domain(domain)
        catalog = self._catalog(domain)
        if item_id not in catalog.items.index:
            raise ItemNotFoundError(
                f"Item '{item_id}' was not found in the {DOMAINS[domain].label} catalog."
            )
        row = catalog.items.loc[item_id]
        return {
            "item_id": item_id,
            "product_title": row["product_title"],
            "price": _clean_number(row["price"], 2),
            "num_ratings": _clean_int(row["num_ratings"]),
        }

    # --------------------------------------------------------
    # Candidate generators (all delegate to existing model code)
    # --------------------------------------------------------

    def _content_candidates(self, domain: str, item_id: str, n: int) -> pd.DataFrame:
        model = self._content_model(domain)
        valid_ids = self._catalog(domain).items.index
        # Over-fetch: some neighbours are the source item itself or have no
        # usable title/ratings, and are removed below.
        similar = recommend_similar_items(model, item_id, top_n=n * 3 + 2)
        if similar.empty:
            return pd.DataFrame(columns=["item_id", "product_title", "score"])
        frame = similar.rename(columns={"similarity": "score"})
        frame = frame[
            (frame["item_id"] != item_id)
            & (frame["score"] > 0)
            & frame["item_id"].isin(valid_ids)
        ]
        return frame.head(n).reset_index(drop=True)

    def _cf_candidates(self, domain: str, item_id: str, n: int) -> pd.DataFrame:
        model = self._cf_model(domain)
        valid_ids = self._catalog(domain).items.index
        indices, distances = get_similar_items(model, item_id, n_neighbors=n * 3 + 2)
        if len(indices) == 0:
            return pd.DataFrame(columns=["item_id", "score"])
        item_ids = model["item_encoder"].inverse_transform(indices)
        frame = pd.DataFrame({"item_id": item_ids, "score": 1.0 - distances})
        frame = frame[
            (frame["item_id"] != item_id)
            & (frame["score"] > 0)
            & frame["item_id"].isin(valid_ids)
        ]
        return frame.head(n).reset_index(drop=True)

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    def recommend(
        self,
        domain: str,
        item_id: str,
        method: str = "hybrid",
        top_n: int = DEFAULT_TOP_N,
    ) -> dict:
        domain = self._validate_domain(domain)
        method = self._validate_method(method)
        top_n = self._validate_top_n(top_n)

        source = self.get_item(domain, item_id)  # raises ItemNotFoundError
        started = time.perf_counter()

        message: str | None = None
        method_used = method
        details: dict[str, dict] = {}

        if method == "content":
            frame = self._content_candidates(domain, item_id, top_n)
            if frame.empty:
                message = "No similar items were found using item descriptions."

        elif method == "cf":
            frame = self._cf_candidates(domain, item_id, top_n)
            if frame.empty:
                message = (
                    "No collaborative-filtering neighbours were found for this item."
                )

        else:  # hybrid
            size = max(HYBRID_CANDIDATE_SIZE, top_n)
            content: pd.DataFrame | None = None
            cf: pd.DataFrame | None = None
            problems: list[str] = []

            try:
                content = self._content_candidates(domain, item_id, size)
            except MethodUnavailableError as error:
                problems.append(str(error))
            try:
                cf = self._cf_candidates(domain, item_id, size)
            except MethodUnavailableError as error:
                problems.append(str(error))

            if content is None and cf is None:
                raise MethodUnavailableError(
                    "Hybrid recommendations are unavailable because neither "
                    "underlying model could be loaded. " + " ".join(problems)
                )

            if content is None or cf is None:
                # Degrade gracefully: keep the app useful, tell the user why.
                logger.warning("Hybrid degraded to a single model: %s", problems)
                if content is None:
                    method_used, frame, missing = "cf", cf.head(top_n), "content-based"
                    used_label = "collaborative-filtering"
                else:
                    method_used, frame, missing = "content", content.head(top_n), "collaborative"
                    used_label = "content-based"
                message = (
                    f"The {missing} model could not be loaded on this machine, so "
                    f"{used_label} results are shown instead of a hybrid ranking. "
                    + " ".join(problems)
                )
            else:
                fused = build_hybrid_recommendations(
                    cf_scores=cf.rename(columns={"score": "cf_score"})[
                        ["item_id", "cf_score"]
                    ],
                    content_scores=content.rename(columns={"score": "content_score"})[
                        ["item_id", "content_score"]
                    ],
                    top_n=top_n,
                    cf_weight=HYBRID_CF_WEIGHT,
                    content_weight=HYBRID_CONTENT_WEIGHT,
                    rrf_k=HYBRID_RRF_K,
                )
                frame = fused.rename(columns={"hybrid_score": "score"})
                for row in fused.itertuples():
                    details[row.item_id] = {
                        "cf_rank": _clean_int(row.cf_rank),
                        "content_rank": _clean_int(row.content_rank),
                        "cf_score": _clean_number(row.cf_score, 4),
                        "content_score": _clean_number(row.content_score, 4),
                    }
                if frame.empty:
                    message = "No hybrid recommendations were found for this item."
                elif cf.empty:
                    message = (
                        "This item has no collaborative signal, so the hybrid "
                        "ranking is based on content similarity only."
                    )

        recommendations = self._to_records(
            domain, frame, method_used, details
        )

        return {
            "domain": domain,
            "method": method,
            "method_used": method_used,
            "top_n": top_n,
            "source_item": source,
            "recommendations": recommendations,
            "count": len(recommendations),
            "message": message,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    def _to_records(
        self,
        domain: str,
        frame: pd.DataFrame,
        method: str,
        details: dict[str, dict],
    ) -> list[dict]:
        if frame.empty:
            return []

        catalog_items = self._catalog(domain).items
        score_type = SCORE_TYPES[method]
        has_title = "product_title" in frame.columns
        records: list[dict] = []

        for rank, row in enumerate(frame.itertuples(index=False), start=1):
            item_id = row.item_id
            in_catalog = item_id in catalog_items.index
            catalog_row = catalog_items.loc[item_id] if in_catalog else None

            title = catalog_row["product_title"] if in_catalog else None
            if not title and has_title:
                title = getattr(row, "product_title", None)
            if not isinstance(title, str) or not title.strip():
                title = "Untitled item"

            record = {
                "rank": rank,
                "item_id": item_id,
                "product_title": title,
                "score": _clean_number(row.score, 6),
                "score_type": score_type,
                "method": method,
                "price": _clean_number(catalog_row["price"], 2) if in_catalog else None,
                "num_ratings": _clean_int(catalog_row["num_ratings"]) if in_catalog else None,
            }
            if item_id in details:
                record["details"] = details[item_id]
            records.append(record)

        return records

    # --------------------------------------------------------
    # Introspection
    # --------------------------------------------------------

    def status(self) -> dict:
        domains = {}
        for key, cfg in DOMAINS.items():
            domains[key] = {
                "label": cfg.label,
                "catalog_loaded": (key, "catalog") in self._cache,
                "content_model_loaded": (key, "content") in self._cache,
                "cf_model_loaded": (key, "cf") in self._cache,
                "build_seconds": {
                    kind: self._build_seconds[(key, kind)]
                    for kind in ("catalog", "content", "cf")
                    if (key, kind) in self._build_seconds
                },
            }
        memory = None
        if psutil is not None:
            vm = psutil.virtual_memory()
            memory = {
                "available_gb": round(vm.available / 1024 ** 3, 1),
                "total_gb": round(vm.total / 1024 ** 3, 1),
            }
        return {"domains": domains, "memory": memory}


@lru_cache(maxsize=1)
def get_service() -> RecommenderService:
    """Process-wide shared service instance."""
    return RecommenderService()

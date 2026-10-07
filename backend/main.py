"""
RecomAI - FastAPI backend.

Run from the project root:

    python -m uvicorn backend.main:app --reload

Interactive API docs:  http://localhost:8000/docs

This module is only an HTTP layer. All recommendation work is delegated to
`src.recommender_service`, which lazily loads and caches the existing models.
Nothing heavy is loaded at startup - models are built on first use.

Environment variables
---------------------
CORS_ORIGINS
    Comma-separated list of allowed browser origins, e.g.
    "https://recomai.example.com,http://localhost:5173".
    If unset, any localhost / 127.0.0.1 port is allowed (local development).
RECOMMENDER_MEMORY_GUARD
    Set to "0" to disable the free-memory check before building models.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.recommender_service import (
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_TOP_N,
    DOMAINS,
    MAX_SEARCH_LIMIT,
    MAX_TOP_N,
    MIN_QUERY_LENGTH,
    InvalidRequestError,
    ItemNotFoundError,
    MethodUnavailableError,
    get_service,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("recomai.api")

service = get_service()


# ============================================================
# Response schemas
# ============================================================

class ItemSummary(BaseModel):
    item_id: str
    product_title: str
    price: Optional[float] = None
    num_ratings: Optional[int] = None


class SearchResponse(BaseModel):
    domain: str
    query: str
    count: int
    results: list[ItemSummary]


class HybridDetails(BaseModel):
    """Per-model ranks/scores behind a hybrid result (None = not in that list)."""

    cf_rank: Optional[int] = None
    content_rank: Optional[int] = None
    cf_score: Optional[float] = None
    content_score: Optional[float] = None


class Recommendation(BaseModel):
    rank: int
    item_id: str
    product_title: str
    score: Optional[float] = None
    # Scores are NOT comparable across methods or probabilities - see score_type.
    score_type: str
    method: str
    price: Optional[float] = None
    num_ratings: Optional[int] = None
    details: Optional[HybridDetails] = None


class RecommendationResponse(BaseModel):
    domain: str
    method: str                 # what the client asked for
    method_used: str            # what actually produced the results
    top_n: int
    source_item: ItemSummary
    recommendations: list[Recommendation]
    count: int
    message: Optional[str] = None
    elapsed_ms: int


class HealthResponse(BaseModel):
    status: str


# ============================================================
# Error handling
# ============================================================

def _call(action: str, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Run a service call and translate service errors into HTTP errors.

    Errors are converted inside the endpoint (rather than with global
    exception handlers) so that every error response still passes through the
    CORS middleware and the browser can read it.
    """
    try:
        return function(*args, **kwargs)
    except InvalidRequestError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except ItemNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except MethodUnavailableError as error:
        raise HTTPException(
            status_code=503, detail=str(error), headers={"Retry-After": "30"}
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while trying to %s", action)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error while trying to {action}. "
            "See the backend log for details.",
        )


# ============================================================
# App
# ============================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "RecomAI API ready. Catalogs and models load lazily on first request."
    )
    yield


app = FastAPI(
    title="RecomAI API",
    description=(
        "HTTP API for the Amazon Reviews 2023 Movies & TV and Video Games "
        "recommendation system. Item-seeded recommendations using content-based "
        "similarity, item-based collaborative filtering, and a weighted "
        "Reciprocal Rank Fusion hybrid. Models load lazily on first use."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

_origins_env = os.getenv("CORS_ORIGINS", "").strip()
if _origins_env:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _origins_env.split(",") if o.strip()],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )


# ------------------------------------------------------------
# General endpoints
# ------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": "RecomAI API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health() -> dict:
    """Liveness check. Does not load any model."""
    return {"status": "healthy"}


@app.get("/api/status", tags=["System"])
def status() -> dict:
    """Which catalogs/models are currently loaded, build times, free memory."""
    return service.status()


# ------------------------------------------------------------
# Per-domain endpoints (movies / games)
# ------------------------------------------------------------

def _build_domain_router(domain: str) -> APIRouter:
    label = DOMAINS[domain].label
    router = APIRouter(prefix=f"/api/{domain}", tags=[label])

    @router.get(
        "/search",
        response_model=SearchResponse,
        summary=f"Search {label} by title",
    )
    def search(
        q: str = Query(
            ...,
            min_length=MIN_QUERY_LENGTH,
            max_length=100,
            description="Title text. Case-insensitive; every word must match.",
        ),
        limit: int = Query(
            DEFAULT_SEARCH_LIMIT,
            ge=1,
            le=MAX_SEARCH_LIMIT,
            description="Maximum number of results.",
        ),
    ) -> dict:
        results = _call(f"search {label}", service.search, domain, q, limit)
        return {"domain": domain, "query": q, "count": len(results), "results": results}

    @router.get(
        "/items/{item_id}",
        response_model=ItemSummary,
        summary=f"Get one {label} item",
    )
    def get_item(item_id: str) -> dict:
        return _call(f"look up an item in {label}", service.get_item, domain, item_id)

    @router.get(
        "/recommendations",
        response_model=RecommendationResponse,
        summary=f"Recommend {label} similar to an item",
    )
    def recommendations(
        item_id: str = Query(
            ...,
            min_length=1,
            max_length=64,
            pattern=r"^[A-Za-z0-9_\-]+$",
            description="item_id returned by the search endpoint.",
        ),
        method: Literal["content", "cf", "hybrid"] = Query(
            "hybrid",
            description=(
                "content = TF-IDF similarity of titles/descriptions/categories; "
                "cf = item-based collaborative filtering; "
                "hybrid = weighted Reciprocal Rank Fusion of both."
            ),
        ),
        top_n: int = Query(
            DEFAULT_TOP_N,
            ge=1,
            le=MAX_TOP_N,
            description="Number of recommendations to return.",
        ),
    ) -> dict:
        return _call(
            f"generate {label} recommendations",
            service.recommend,
            domain,
            item_id,
            method,
            top_n,
        )

    return router


for _domain in DOMAINS:
    app.include_router(_build_domain_router(_domain))

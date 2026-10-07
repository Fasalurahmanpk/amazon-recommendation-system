from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from src.config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)


# ============================================================
# 5-CORE FILTERING
# ============================================================

def get_5core_ids(reviews_path, min_interactions=5):
    """
    Find users and items that have at least
    `min_interactions` reviews.
    """

    lazy_reviews = pl.scan_ndjson(reviews_path)

    user_counts = (
        lazy_reviews
        .group_by("user_id")
        .len()
        .filter(
            pl.col("len") >= min_interactions
        )
        .collect(engine="streaming")
    )

    item_counts = (
        lazy_reviews
        .group_by("parent_asin")
        .len()
        .filter(
            pl.col("len") >= min_interactions
        )
        .collect(engine="streaming")
    )

    valid_users = set(user_counts["user_id"])
    valid_items = set(item_counts["parent_asin"])

    return valid_users, valid_items


# ============================================================
# FILTER REVIEWS
# ============================================================

def filter_reviews_to_parquet(
    reviews_path,
    valid_users,
    valid_items,
    output_path,
):
    """
    Filter reviews to the 5-core subset
    and save directly as Parquet.
    """

    (
        pl.scan_ndjson(reviews_path)
        .select([
            "rating",
            "user_id",
            "parent_asin",
            "timestamp",
        ])
        .filter(
            pl.col("user_id").is_in(valid_users)
            & pl.col("parent_asin").is_in(valid_items)
        )
        .sink_parquet(output_path)
    )

    return pl.read_parquet(output_path)


# ============================================================
# FILTER METADATA
# ============================================================

def filter_metadata_to_parquet(
    metadata_path,
    valid_items,
    output_path,
):
    """
    Filter product metadata to items
    present in the 5-core dataset.
    """

    (
        pl.scan_ndjson(
            metadata_path,
            schema_overrides={
                "price": pl.Utf8
            },
        )
        .select([
            "parent_asin",
            "title",
            "description",
            "price",
            "categories",
        ])
        .filter(
            pl.col("parent_asin").is_in(valid_items)
        )
        .sink_parquet(output_path)
    )

    return pl.read_parquet(output_path)


# ============================================================
# PROCESS ONE CATEGORY
# ============================================================

def process_category(
    category_name,
    reviews_path,
    metadata_path,
):
    """
    Run 5-core filtering for one Amazon category.

    If the reviews Parquet file already exists,
    it will be reused instead of filtering the
    large JSONL file again.
    """

    category_dir = PROCESSED_DATA_DIR

    reviews_output = (
        category_dir
        / f"{category_name}_reviews_5core.parquet"
    )

    metadata_output = (
        category_dir
        / f"{category_name}_meta_5core.parquet"
    )

    # --------------------------------------------------------
    # Count valid users and items
    # --------------------------------------------------------

    print(
        f"\n--- {category_name}: counting interactions ---"
    )

    valid_users, valid_items = get_5core_ids(
        reviews_path
    )

    print(
        f"{category_name}: "
        f"{len(valid_users):,} valid users | "
        f"{len(valid_items):,} valid items"
    )

    # --------------------------------------------------------
    # Reviews
    # --------------------------------------------------------

    if reviews_output.exists():

        print(
            f"--- {category_name}: "
            f"existing reviews file found ---"
        )

        reviews_df = pl.read_parquet(
            reviews_output
        )

        print(
            f"{category_name} reviews loaded: "
            f"{reviews_df.shape}"
        )

    else:

        print(
            f"--- {category_name}: "
            f"filtering reviews ---"
        )

        reviews_df = filter_reviews_to_parquet(
            reviews_path,
            valid_users,
            valid_items,
            reviews_output,
        )

        print(
            f"{category_name} reviews: "
            f"{reviews_df.shape}"
        )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    if metadata_output.exists():

        print(
            f"--- {category_name}: "
            f"existing metadata file found ---"
        )

        metadata_df = pl.read_parquet(
            metadata_output
        )

        print(
            f"{category_name} metadata loaded: "
            f"{metadata_df.shape}"
        )

    else:

        print(
            f"--- {category_name}: "
            f"filtering metadata ---"
        )

        metadata_df = filter_metadata_to_parquet(
            metadata_path,
            valid_items,
            metadata_output,
        )

        print(
            f"{category_name} metadata: "
            f"{metadata_df.shape}"
        )

    # --------------------------------------------------------
    # Return Pandas DataFrames
    # --------------------------------------------------------

    return (
        reviews_df.to_pandas(),
        metadata_df.to_pandas(),
    )


# ============================================================
# STANDARDIZATION & CLEANING
# ============================================================

def load_and_clean(
    reviews_df,
    metadata_df,
    category_name,
):
    """
    Standardize and clean ratings and metadata.
    """

    # --------------------------------------------------------
    # Ratings
    # --------------------------------------------------------

    ratings_df = reviews_df.rename(
        columns={
            "parent_asin": "item_id"
        }
    ).copy()

    ratings_df["rating"] = pd.to_numeric(
        ratings_df["rating"],
        errors="coerce",
    )

    ratings_df = ratings_df.dropna(
        subset=["rating"]
    )

    ratings_df = (
        ratings_df
        .sort_values("timestamp")
        .drop_duplicates(
            subset=[
                "user_id",
                "item_id",
            ],
            keep="last",
        )
    )

    # --------------------------------------------------------
    # Rating Centering
    # --------------------------------------------------------

    user_mean = (
        ratings_df
        .groupby("user_id")["rating"]
        .transform("mean")
    )

    ratings_df["rating_centered"] = (
        ratings_df["rating"] - user_mean
    )

    # --------------------------------------------------------
    # Rating Normalization
    # --------------------------------------------------------

    rating_min = ratings_df["rating"].min()
    rating_max = ratings_df["rating"].max()

    ratings_df["rating_normalized"] = (
        (
            ratings_df["rating"]
            - rating_min
        )
        / (rating_max - rating_min)
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata_df = metadata_df.rename(
        columns={
            "parent_asin": "item_id",
            "title": "product_title",
        }
    ).copy()

    def flatten_description(value):
        if isinstance(
            value,
            (list, np.ndarray),
        ):
            return " ".join(
                str(v)
                for v in value
            )

        if isinstance(value, str):
            return value

        return ""

    metadata_df["description"] = (
        metadata_df["description"]
        .apply(flatten_description)
    )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    metadata_df["price"] = (
        metadata_df["price"]
        .replace("—", pd.NA)
    )

    metadata_df["price"] = pd.to_numeric(
        metadata_df["price"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Dataset Statistics
    # --------------------------------------------------------

    n_users = (
        ratings_df["user_id"]
        .nunique()
    )

    n_items = (
        ratings_df["item_id"]
        .nunique()
    )

    sparsity = (
        1
        - len(ratings_df)
        / (n_users * n_items)
    )

    return {
        "ratings_df": ratings_df,
        "metadata_df": metadata_df,
        "category": category_name,
        "n_users": n_users,
        "n_items": n_items,
        "sparsity": sparsity,
    }


# ============================================================
# TIME-AWARE TRAIN / TEST SPLIT
# ============================================================

def time_based_train_test_split(
    ratings_df,
    test_size=0.2,
    min_ratings=5,
):
    """
    Split each user's interactions chronologically.

    Oldest 80% -> training
    Most recent 20% -> testing

    Users with fewer than `min_ratings`
    remain entirely in training.
    """

    df = (
        ratings_df
        .sort_values(
            [
                "user_id",
                "timestamp",
            ]
        )
        .reset_index(drop=True)
    )

    group_sizes = (
        df.groupby("user_id")["user_id"]
        .transform("size")
    )

    rank_in_group = (
        df.groupby("user_id")
        .cumcount()
    )

    n_test = np.where(
        group_sizes < min_ratings,
        0,
        np.maximum(
            1,
            np.round(
                group_sizes
                * test_size
            ),
        ),
    ).astype(int)

    n_test = np.minimum(
        n_test,
        group_sizes - 1,
    )

    threshold = (
        group_sizes - n_test
    )

    is_test = (
        rank_in_group.to_numpy()
        >= threshold.to_numpy()
    )

    train_df = (
        df.loc[~is_test]
        .reset_index(drop=True)
    )

    test_df = (
        df.loc[is_test]
        .reset_index(drop=True)
    )

    return train_df, test_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Video Games
    # --------------------------------------------------------

    process_category(
        category_name="games",
        reviews_path=(
            RAW_DATA_DIR
            / "games"
            / "Video_Games.jsonl"
        ),
        metadata_path=(
            RAW_DATA_DIR
            / "games"
            / "meta_Video_Games.jsonl"
        ),
    )

    # --------------------------------------------------------
    # Movies & TV
    # --------------------------------------------------------

    process_category(
        category_name="movies",
        reviews_path=(
            RAW_DATA_DIR
            / "movies"
            / "Movies_and_TV.jsonl"
        ),
        metadata_path=(
            RAW_DATA_DIR
            / "movies"
            / "meta_Movies_and_TV.jsonl"
        ),
    )
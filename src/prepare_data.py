from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DATA_DIR


# ============================================================
# CONFIGURATION
# ============================================================

TEST_SIZE = 0.20
MIN_RATINGS = 5


# ============================================================
# LOAD 5-CORE DATA
# ============================================================

def load_5core_data(category):
    """
    Load 5-core reviews and metadata for a category.
    """

    reviews_path = (
        PROCESSED_DATA_DIR
        / f"{category}_reviews_5core.parquet"
    )

    metadata_path = (
        PROCESSED_DATA_DIR
        / f"{category}_meta_5core.parquet"
    )

    print(f"\nLoading {category} data...")

    reviews_df = pd.read_parquet(reviews_path)
    metadata_df = pd.read_parquet(metadata_path)

    print(f"Reviews : {reviews_df.shape}")
    print(f"Metadata: {metadata_df.shape}")

    return reviews_df, metadata_df


# ============================================================
# CLEAN RATINGS
# ============================================================

def clean_ratings(reviews_df):
    """
    Standardize and clean the ratings dataframe.
    """

    ratings_df = reviews_df.rename(
        columns={
            "parent_asin": "item_id"
        }
    ).copy()

    # Convert rating to numeric
    ratings_df["rating"] = pd.to_numeric(
        ratings_df["rating"],
        errors="coerce",
    )

    # Remove invalid ratings
    ratings_df = ratings_df.dropna(
        subset=["rating"]
    )

    # Sort chronologically
    ratings_df = ratings_df.sort_values(
        "timestamp"
    )

    # Keep the latest interaction for each
    # user-item pair
    ratings_df = ratings_df.drop_duplicates(
        subset=[
            "user_id",
            "item_id",
        ],
        keep="last",
    )

    # --------------------------------------------------------
    # User mean rating
    # --------------------------------------------------------

    user_mean = (
        ratings_df
        .groupby("user_id")["rating"]
        .transform("mean")
    )

    # Center rating around user's average
    ratings_df["rating_centered"] = (
        ratings_df["rating"]
        - user_mean
    )

    # --------------------------------------------------------
    # Normalize ratings to [0, 1]
    # --------------------------------------------------------

    rating_min = ratings_df["rating"].min()
    rating_max = ratings_df["rating"].max()

    if rating_max != rating_min:
        ratings_df["rating_normalized"] = (
            ratings_df["rating"] - rating_min
        ) / (rating_max - rating_min)
    else:
        ratings_df["rating_normalized"] = 0.0

    return ratings_df


# ============================================================
# CLEAN METADATA
# ============================================================

def clean_metadata(metadata_df):
    """
    Standardize and clean product metadata.
    """

    metadata_df = metadata_df.rename(
        columns={
            "parent_asin": "item_id",
            "title": "product_title",
        }
    ).copy()

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    def flatten_description(value):

        if isinstance(value, list):
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

    return metadata_df


# ============================================================
# TIME-BASED TRAIN / TEST SPLIT
# ============================================================

def time_based_train_test_split(
    ratings_df,
    test_size=TEST_SIZE,
    min_ratings=MIN_RATINGS,
):
    """
    Split each user's interactions chronologically.

    Oldest 80% -> training
    Newest 20% -> testing

    Users with fewer than min_ratings remain
    completely in the training set.
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

    # Number of test interactions per user
    n_test = (
        group_sizes * test_size
    ).round().astype(int)

    # Users with fewer than min_ratings
    # remain completely in training
    n_test = n_test.where(
        group_sizes >= min_ratings,
        0,
    )

    # At least one test interaction for
    # eligible users
    n_test = n_test.where(
        group_sizes < min_ratings,
        n_test.clip(lower=1),
    )

    # Never put all interactions into test
    n_test = n_test.clip(
        upper=group_sizes - 1
    )

    threshold = (
        group_sizes - n_test
    )

    is_test = (
        rank_in_group >= threshold
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
# PROCESS ONE CATEGORY
# ============================================================

def prepare_category(category):
    """
    Complete cleaning and train/test preparation
    for one category.
    """

    reviews_df, metadata_df = (
        load_5core_data(category)
    )

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    print(
        f"\nCleaning {category} ratings..."
    )

    ratings_df = clean_ratings(
        reviews_df
    )

    print(
        f"Clean ratings: {ratings_df.shape}"
    )

    print(
        f"\nCleaning {category} metadata..."
    )

    metadata_df = clean_metadata(
        metadata_df
    )

    print(
        f"Clean metadata: {metadata_df.shape}"
    )

    # --------------------------------------------------------
    # Save cleaned data
    # --------------------------------------------------------

    clean_ratings_path = (
        PROCESSED_DATA_DIR
        / f"{category}_clean_ratings.parquet"
    )

    clean_metadata_path = (
        PROCESSED_DATA_DIR
        / f"{category}_clean_meta.parquet"
    )

    ratings_df.to_parquet(
        clean_ratings_path,
        index=False,
    )

    metadata_df.to_parquet(
        clean_metadata_path,
        index=False,
    )

    print(
        f"\nSaved: {clean_ratings_path}"
    )

    print(
        f"Saved: {clean_metadata_path}"
    )

    # --------------------------------------------------------
    # Train / Test split
    # --------------------------------------------------------

    print(
        f"\nCreating time-based split "
        f"for {category}..."
    )

    train_df, test_df = (
        time_based_train_test_split(
            ratings_df
        )
    )

    print(
        f"Train: {train_df.shape}"
    )

    print(
        f"Test : {test_df.shape}"
    )

    # --------------------------------------------------------
    # Save train/test
    # --------------------------------------------------------

    train_path = (
        PROCESSED_DATA_DIR
        / f"{category}_train.parquet"
    )

    test_path = (
        PROCESSED_DATA_DIR
        / f"{category}_test.parquet"
    )

    train_df.to_parquet(
        train_path,
        index=False,
    )

    test_df.to_parquet(
        test_path,
        index=False,
    )

    print(
        f"\nSaved: {train_path}"
    )

    print(
        f"Saved: {test_path}"
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        f"\n========== {category.upper()} SUMMARY =========="
    )

    print(
        f"Users : {ratings_df['user_id'].nunique():,}"
    )

    print(
        f"Items : {ratings_df['item_id'].nunique():,}"
    )

    print(
        f"Ratings: {len(ratings_df):,}"
    )

    print(
        f"Train : {len(train_df):,}"
    )

    print(
        f"Test  : {len(test_df):,}"
    )

    print("=" * 50)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # Start with Games.
    # We will verify it before processing Movies.

    prepare_category("movies")

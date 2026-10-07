import numpy as np
import pandas as pd


# ============================================================
# 1. Get Collaborative Filtering Candidates
# ============================================================

def get_collaborative_scores(
    user_cf_data,
    train_ratings_df,
    user_id,
    top_n=50
):
    """
    Generate candidate recommendations using
    User-Based Collaborative Filtering.
    """

    from models.collaborative_filtering.collaborative_filtering import (
        recommend_items_user_cf
    )

    # Minimal metadata required by the CF recommendation function
    metadata_df = (
        train_ratings_df[["item_id"]]
        .drop_duplicates()
        .assign(product_title="")
    )

    recommendations = recommend_items_user_cf(
        user_cf_data,
        train_ratings_df,
        metadata_df=metadata_df,
        user_id=user_id,
        top_n=top_n
    )

    if recommendations.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "cf_score"
            ]
        )

    return recommendations[
        ["item_id", "score"]
    ].rename(
        columns={
            "score": "cf_score"
        }
    )


# ============================================================
# 2. Get Content-Based Candidates
# ============================================================

def get_content_scores(
    content_model,
    train_ratings_df,
    user_id,
    top_n=50
):
    """
    Generate candidate recommendations using
    Content-Based Filtering.
    """

    from models.content_based.content_based import (
        recommend_items_content_based
    )

    recommendations = recommend_items_content_based(
        content_model,
        train_ratings_df,
        user_id=user_id,
        top_n=top_n
    )

    if recommendations.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "content_score"
            ]
        )

    return recommendations[
        ["item_id", "score"]
    ].rename(
        columns={
            "score": "content_score"
        }
    )


# ============================================================
# 3. Weighted Reciprocal Rank Fusion
# ============================================================

def build_hybrid_recommendations(
    cf_scores,
    content_scores,
    top_n=10,
    cf_weight=0.5,
    content_weight=0.5,
    rrf_k=60
):
    """
    Combine Collaborative Filtering and Content-Based
    recommendation rankings using Weighted Reciprocal
    Rank Fusion (RRF).

    RRF formula:

        RRF = 1 / (k + rank)

    Final hybrid score:

        Hybrid Score =
            CF Weight × CF RRF
            +
            Content Weight × Content RRF
    """

    # --------------------------------------------------------
    # Copy input DataFrames
    # --------------------------------------------------------

    cf = cf_scores.copy()
    content = content_scores.copy()

    # --------------------------------------------------------
    # Create CF ranking
    # --------------------------------------------------------

    if not cf.empty:

        cf = (
            cf
            .sort_values(
                "cf_score",
                ascending=False
            )
            .reset_index(drop=True)
        )

        cf["cf_rank"] = np.arange(
            1,
            len(cf) + 1
        )

        # Reciprocal Rank Fusion score
        cf["cf_rrf"] = (
            1.0
            / (rrf_k + cf["cf_rank"])
        )

    # --------------------------------------------------------
    # Create Content-Based ranking
    # --------------------------------------------------------

    if not content.empty:

        content = (
            content
            .sort_values(
                "content_score",
                ascending=False
            )
            .reset_index(drop=True)
        )

        content["content_rank"] = np.arange(
            1,
            len(content) + 1
        )

        # Reciprocal Rank Fusion score
        content["content_rrf"] = (
            1.0
            / (
                rrf_k
                + content["content_rank"]
            )
        )

    # --------------------------------------------------------
    # Select required columns
    # --------------------------------------------------------

    cf_columns = [
        "item_id",
        "cf_score",
        "cf_rank",
        "cf_rrf"
    ]

    content_columns = [
        "item_id",
        "content_score",
        "content_rank",
        "content_rrf"
    ]

    if cf.empty:
        cf = pd.DataFrame(
            columns=cf_columns
        )
    else:
        cf = cf[cf_columns]

    if content.empty:
        content = pd.DataFrame(
            columns=content_columns
        )
    else:
        content = content[content_columns]

    # --------------------------------------------------------
    # Merge candidate lists
    # --------------------------------------------------------

    hybrid = pd.merge(
        cf,
        content,
        on="item_id",
        how="outer"
    )

    if hybrid.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "cf_score",
                "content_score",
                "cf_rank",
                "content_rank",
                "hybrid_score"
            ]
        )

    # --------------------------------------------------------
    # Missing RRF scores become zero
    #
    # This is appropriate here because RRF is based on
    # ranking contribution. If an item is absent from a
    # candidate list, that model contributes no rank score.
    # --------------------------------------------------------

    hybrid["cf_rrf"] = (
        hybrid["cf_rrf"]
        .fillna(0)
    )

    hybrid["content_rrf"] = (
        hybrid["content_rrf"]
        .fillna(0)
    )

    # --------------------------------------------------------
    # Calculate Weighted RRF score
    # --------------------------------------------------------

    hybrid["hybrid_score"] = (
        cf_weight * hybrid["cf_rrf"]
        +
        content_weight * hybrid["content_rrf"]
    )

    # --------------------------------------------------------
    # Sort by final Hybrid score
    # --------------------------------------------------------

    hybrid = (
        hybrid
        .sort_values(
            "hybrid_score",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    return hybrid[
        [
            "item_id",
            "cf_score",
            "content_score",
            "cf_rank",
            "content_rank",
            "hybrid_score"
        ]
    ]


# ============================================================
# 4. Complete Hybrid Recommendation Pipeline
# ============================================================

def recommend_items_hybrid(
    user_cf_data,
    content_model,
    train_ratings_df,
    user_id,
    top_n=10,
    candidate_size=50,
    cf_weight=0.5,
    content_weight=0.5,
    rrf_k=60
):
    """
    Generate personalized recommendations using:

        User-Based Collaborative Filtering
                         +
                   Content-Based
                         ↓
              Weighted RRF Hybrid
    """

    # --------------------------------------------------------
    # Step 1: Generate CF candidates
    # --------------------------------------------------------

    cf_scores = get_collaborative_scores(
        user_cf_data,
        train_ratings_df,
        user_id=user_id,
        top_n=candidate_size
    )

    # --------------------------------------------------------
    # Step 2: Generate Content-Based candidates
    # --------------------------------------------------------

    content_scores = get_content_scores(
        content_model,
        train_ratings_df,
        user_id=user_id,
        top_n=candidate_size
    )

    # --------------------------------------------------------
    # Step 3: Combine using Weighted RRF
    # --------------------------------------------------------

    recommendations = build_hybrid_recommendations(
        cf_scores=cf_scores,
        content_scores=content_scores,
        top_n=top_n,
        cf_weight=cf_weight,
        content_weight=content_weight,
        rrf_k=rrf_k
    )

    return recommendations

def evaluate_hybrid_precision_at_10(
    user_cf_data,
    content_model,
    train_ratings_df,
    test_ratings_df,
    sample_users=100,
    candidate_size=50,
    cf_weight=0.5,
    content_weight=0.5,
    rrf_k=60
):
    """
    Evaluate the Hybrid recommender using Precision@10.

    Relevant items are test items with rating >= 4.
    """

    test_users = test_ratings_df["user_id"].unique()

    rng = np.random.RandomState(42)

    selected_users = rng.choice(
        test_users,
        size=min(sample_users, len(test_users)),
        replace=False
    )

    precisions = []
    evaluated_users = 0

    for user_id in selected_users:

        # Items the user actually liked in the test set
        relevant_items = set(
            test_ratings_df.loc[
                (test_ratings_df["user_id"] == user_id)
                & (test_ratings_df["rating"] >= 4),
                "item_id"
            ]
        )

        if len(relevant_items) == 0:
            continue

        # Generate hybrid recommendations
        recommendations = recommend_items_hybrid(
            user_cf_data=user_cf_data,
            content_model=content_model,
            train_ratings_df=train_ratings_df,
            user_id=user_id,
            top_n=10,
            candidate_size=candidate_size,
            cf_weight=cf_weight,
            content_weight=content_weight,
            rrf_k=rrf_k
        )

        if recommendations.empty:
            continue

        recommended_items = recommendations[
            "item_id"
        ].tolist()

        hits = sum(
            item in relevant_items
            for item in recommended_items
        )

        precision = hits / len(recommended_items)

        precisions.append(precision)
        evaluated_users += 1

    if len(precisions) == 0:
        return None

    return {
        "Model": "Hybrid RRF",
        "Precision@10": np.mean(precisions),
        "Evaluated Users": evaluated_users
    }
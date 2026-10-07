"""
User-Based and Item-Based Collaborative Filtering

This module contains the core collaborative filtering models
used in the Personalized Entertainment Recommendation System.
"""

import numpy as np
import pandas as pd

from scipy.sparse import csr_matrix
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import NearestNeighbors


# Model configuration
CF_N_NEIGHBORS = 20


def build_user_cf_model(train_ratings_df, n_neighbors=CF_N_NEIGHBORS):
    """
    Build a User-Based Collaborative Filtering model.

    Parameters
    ----------
    train_ratings_df : pandas.DataFrame
        Training ratings containing user_id, item_id, and rating.

    n_neighbors : int
        Number of similar users to retrieve.

    Returns
    -------
    dict
        Trained model components.
    """

    df = train_ratings_df[
        ["user_id", "item_id", "rating"]
    ].copy()

    # Encode users and items into integer indices
    user_encoder = LabelEncoder()
    item_encoder = LabelEncoder()

    df["user"] = user_encoder.fit_transform(df["user_id"])
    df["item"] = item_encoder.fit_transform(df["item_id"])

    # Create sparse User-Item matrix
    user_item_matrix = csr_matrix(
        (
            df["rating"].values,
            (df["user"].values, df["item"].values)
        ),
        shape=(
            len(user_encoder.classes_),
            len(item_encoder.classes_)
        )
    )

    # Find similar users using cosine distance
    model = NearestNeighbors(
        metric="cosine",
        algorithm="brute",
        n_neighbors=n_neighbors
    )

    model.fit(user_item_matrix)

    return {
        "model": model,
        "user_item_matrix": user_item_matrix,
        "user_encoder": user_encoder,
        "item_encoder": item_encoder,
        "ratings_encoded": df[
            ["user", "item", "rating"]
        ]
    }


def get_similar_users(
    user_cf_data,
    user_id,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Find users similar to a given user.

    Parameters
    ----------
    user_cf_data : dict
        Trained User-Based CF model.

    user_id : str
        Original user ID.

    n_neighbors : int
        Number of similar users to retrieve.

    Returns
    -------
    similar_users : numpy.ndarray
        Encoded indices of similar users.

    distances : numpy.ndarray
        Cosine distances from the target user.
    """

    user_encoder = user_cf_data["user_encoder"]
    user_item_matrix = user_cf_data["user_item_matrix"]
    model = user_cf_data["model"]

    # Check whether the user exists
    if user_id not in user_encoder.classes_:
        return np.array([]), np.array([])

    # Convert original user ID to matrix index
    user_index = user_encoder.transform([user_id])[0]

    # Find similar users
    distances, indices = model.kneighbors(
        user_item_matrix[user_index],
        n_neighbors=n_neighbors + 1
    )

    # Remove the user itself
    similar_users = indices[0][1:]
    distances = distances[0][1:]

    return similar_users, distances


def predict_rating_user_cf(
    user_cf_data,
    train_ratings_df,
    user_id,
    item_id,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Predict a user's rating for an item using similar users.

    The prediction is calculated as a similarity-weighted
    average of ratings given by similar users.
    """

    user_encoder = user_cf_data["user_encoder"]
    item_encoder = user_cf_data["item_encoder"]

    # Check whether user and item exist
    if user_id not in user_encoder.classes_:
        return None

    if item_id not in item_encoder.classes_:
        return None

    # Find similar users
    similar_users, distances = get_similar_users(
        user_cf_data,
        user_id,
        n_neighbors=n_neighbors
    )

    if len(similar_users) == 0:
        return None

    # Convert cosine distance to similarity
    similarities = 1 - distances

    # Convert encoded users back to original IDs
    similar_user_ids = user_encoder.inverse_transform(
        similar_users
    )

    # Get ratings given by similar users for this item
    similar_ratings = train_ratings_df[
        train_ratings_df["user_id"].isin(similar_user_ids)
        & (train_ratings_df["item_id"] == item_id)
    ].copy()

    if similar_ratings.empty:
        return None

    # Map each user's similarity
    similarity_map = dict(
        zip(similar_user_ids, similarities)
    )

    similar_ratings["similarity"] = (
        similar_ratings["user_id"].map(similarity_map)
    )

    # Avoid division by zero
    similarity_sum = similar_ratings["similarity"].sum()

    if similarity_sum == 0:
        return None

    # Similarity-weighted rating
    predicted_rating = (
        (
            similar_ratings["rating"]
            * similar_ratings["similarity"]
        ).sum()
        / similarity_sum
    )

    return float(predicted_rating)


def recommend_items_user_cf(
    user_cf_data,
    train_ratings_df,
    metadata_df,
    user_id,
    top_n=10,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Generate Top-N item recommendations for a user
    using User-Based Collaborative Filtering.
    """

    user_encoder = user_cf_data["user_encoder"]

    # Check whether user exists
    if user_id not in user_encoder.classes_:
        return pd.DataFrame(
            columns=[
                "item_id",
                "product_title",
                "score"
            ]
        )

    # Find similar users
    similar_users, distances = get_similar_users(
        user_cf_data,
        user_id,
        n_neighbors=n_neighbors
    )

    if len(similar_users) == 0:
        return pd.DataFrame(
            columns=[
                "item_id",
                "product_title",
                "score"
            ]
        )

    # Convert distance to similarity
    similarities = 1 - distances

    # Convert encoded users to original IDs
    similar_user_ids = user_encoder.inverse_transform(
        similar_users
    )

    # Create similarity mapping
    similarity_map = dict(
        zip(similar_user_ids, similarities)
    )

    # Get ratings from similar users
    similar_ratings = train_ratings_df[
        train_ratings_df["user_id"].isin(similar_user_ids)
    ].copy()

    if similar_ratings.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "product_title",
                "score"
            ]
        )

    # Add similarity score
    similar_ratings["similarity"] = (
        similar_ratings["user_id"].map(similarity_map)
    )

    # Remove items already rated by target user
    user_rated_items = set(
        train_ratings_df.loc[
            train_ratings_df["user_id"] == user_id,
            "item_id"
        ]
    )

    similar_ratings = similar_ratings[
        ~similar_ratings["item_id"].isin(user_rated_items)
    ]

    if similar_ratings.empty:
        return pd.DataFrame(
            columns=[
                "item_id",
                "product_title",
                "score"
            ]
        )

    # Calculate weighted recommendation score
    similar_ratings["weighted_score"] = (
        similar_ratings["rating"]
        * similar_ratings["similarity"]
    )

    recommendation_scores = (
        similar_ratings
        .groupby("item_id")
        .agg(
            weighted_score=("weighted_score", "sum"),
            similarity_sum=("similarity", "sum")
        )
    )

    # Calculate final recommendation score
    recommendation_scores["score"] = (
        recommendation_scores["weighted_score"]
        / recommendation_scores["similarity_sum"]
    )

    # Select Top-N items
    top_items = (
        recommendation_scores
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index()
    )

    # Add item metadata
    recommendations = (
        top_items
        .merge(
            metadata_df[
                ["item_id", "product_title"]
            ],
            on="item_id",
            how="left"
        )
    )

    return recommendations[
        ["item_id", "product_title", "score"]
    ]

def build_item_cf_model(
    train_ratings_df,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Build an Item-Based Collaborative Filtering model.

    Items are compared based on the users who rated them.
    """

    df = train_ratings_df[
        ["user_id", "item_id", "rating"]
    ].copy()

    user_encoder = LabelEncoder()
    item_encoder = LabelEncoder()

    df["user"] = user_encoder.fit_transform(df["user_id"])
    df["item"] = item_encoder.fit_transform(df["item_id"])

    # Item-User Matrix
    item_user_matrix = csr_matrix(
        (
            df["rating"].values,
            (df["item"].values, df["user"].values)
        ),
        shape=(
            len(item_encoder.classes_),
            len(user_encoder.classes_)
        )
    )

    model = NearestNeighbors(
        metric="cosine",
        algorithm="brute",
        n_neighbors=n_neighbors
    )

    model.fit(item_user_matrix)

    return {
        "model": model,
        "item_user_matrix": item_user_matrix,
        "user_encoder": user_encoder,
        "item_encoder": item_encoder,
        "ratings_encoded": df[["user", "item", "rating"]]
    }

def get_similar_items(
    item_cf_data,
    item_id,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Find items similar to the given item.
    """

    item_encoder = item_cf_data["item_encoder"]
    item_user_matrix = item_cf_data["item_user_matrix"]
    model = item_cf_data["model"]

    if item_id not in item_encoder.classes_:
        return np.array([]), np.array([])

    item_index = item_encoder.transform([item_id])[0]

    distances, indices = model.kneighbors(
        item_user_matrix[item_index],
        n_neighbors=n_neighbors + 1
    )

    similar_items = indices[0][1:]
    distances = distances[0][1:]

    return similar_items, distances    

def recommend_items_item_cf(
    item_cf_data,
    train_ratings_df,
    metadata_df,
    user_id,
    top_n=10,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Generate item-based collaborative filtering recommendations
    for a user.
    """

    item_encoder = item_cf_data["item_encoder"]

    # Check whether the user exists
    if user_id not in train_ratings_df["user_id"].values:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Get items already rated by the user
    user_ratings = train_ratings_df[
        train_ratings_df["user_id"] == user_id
    ][["item_id", "rating"]]

    if user_ratings.empty:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    user_rated_items = set(user_ratings["item_id"])

    recommendation_scores = {}

    # Find similar items for every item rated by the user
    for _, row in user_ratings.iterrows():

        rated_item = row["item_id"]
        user_rating = row["rating"]

        # Skip items that are not available in the model
        if rated_item not in item_encoder.classes_:
            continue

        similar_items, distances = get_similar_items(
            item_cf_data,
            rated_item,
            n_neighbors=n_neighbors
        )

        similarities = 1 - distances

        similar_item_ids = item_encoder.inverse_transform(
            similar_items
        )

        for similar_item_id, similarity in zip(
            similar_item_ids,
            similarities
        ):

            # Don't recommend items already rated
            if similar_item_id in user_rated_items:
                continue

            score = similarity * user_rating

            recommendation_scores[similar_item_id] = (
                recommendation_scores.get(
                    similar_item_id,
                    0
                ) + score
            )

    if not recommendation_scores:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Convert scores to DataFrame
    recommendations = pd.DataFrame(
        recommendation_scores.items(),
        columns=["item_id", "score"]
    )

    # Sort by recommendation score
    recommendations = (
        recommendations
        .sort_values(
            "score",
            ascending=False
        )
        .head(top_n)
    )

    # Add game titles
    recommendations = recommendations.merge(
        metadata_df[
            ["item_id", "product_title"]
        ],
        on="item_id",
        how="left"
    )

    return recommendations[
        ["item_id", "product_title", "score"]
    ]

def predict_rating_item_cf(
    item_cf_data,
    train_ratings_df,
    user_id,
    item_id,
    n_neighbors=CF_N_NEIGHBORS
):
    """
    Predict a user's rating for an item using
    similar items.
    """

    item_encoder = item_cf_data["item_encoder"]

    # Check whether the item exists in the model
    if item_id not in item_encoder.classes_:
        return None

    # Get items already rated by the user
    user_ratings = train_ratings_df[
        train_ratings_df["user_id"] == user_id
    ][["item_id", "rating"]]

    if user_ratings.empty:
        return None

    # Don't predict an item the user has already rated
    user_rated_items = set(user_ratings["item_id"])

    if item_id in user_rated_items:
        return None

    weighted_sum = 0.0
    similarity_sum = 0.0

    # Compare the target item with items
    # already rated by the user
    for _, row in user_ratings.iterrows():

        rated_item = row["item_id"]
        user_rating = row["rating"]

        if rated_item not in item_encoder.classes_:
            continue

        similar_items, distances = get_similar_items(
            item_cf_data,
            rated_item,
            n_neighbors=n_neighbors
        )

        similarities = 1 - distances

        similar_item_ids = item_encoder.inverse_transform(
            similar_items
        )

        # Check whether target item is among
        # the similar items
        matches = np.where(
            similar_item_ids == item_id
        )[0]

        if len(matches) == 0:
            continue

        similarity = similarities[matches[0]]

        weighted_sum += (
            similarity * user_rating
        )

        similarity_sum += similarity

    if similarity_sum == 0:
        return None

    predicted_rating = (
        weighted_sum / similarity_sum
    )

    return float(predicted_rating)
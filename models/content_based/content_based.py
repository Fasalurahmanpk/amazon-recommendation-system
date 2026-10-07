import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


def build_content_based_model(
    metadata_df,
    max_features=5000
):
    """
    Build a TF-IDF based content recommendation model.
    """

    metadata = metadata_df[
        ["item_id", "product_title", "description", "categories"]
    ].copy()

    # Convert every text field into a string
    metadata["product_title"] = metadata["product_title"].apply(
        lambda x: " ".join(map(str, x)) if isinstance(x, (list, np.ndarray)) else str(x)
    )

    metadata["description"] = metadata["description"].apply(
        lambda x: " ".join(map(str, x)) if isinstance(x, (list, np.ndarray)) else str(x)
    )

    metadata["categories"] = metadata["categories"].apply(
        lambda x: " ".join(map(str, x)) if isinstance(x, (list, np.ndarray)) else str(x)
    )

    # Replace missing values
    metadata["product_title"] = metadata["product_title"].replace(
        "nan", ""
    )

    metadata["description"] = metadata["description"].replace(
        "nan", ""
    )

    metadata["categories"] = metadata["categories"].replace(
        "nan", ""
    )

    # Combine text information
    metadata["content"] = (
        metadata["product_title"] + " "
        + metadata["description"] + " "
        + metadata["categories"]
    )

    # Convert text into TF-IDF vectors
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english"
    )

    tfidf_matrix = vectorizer.fit_transform(
        metadata["content"]
    )

    # Find similar items using cosine distance
    model = NearestNeighbors(
        metric="cosine",
        algorithm="brute"
    )

    model.fit(tfidf_matrix)

    return {
        "model": model,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "metadata": metadata
    }

def recommend_similar_items(
    content_model,
    item_id,
    top_n=10
):
    model = content_model["model"]
    vectorizer = content_model["vectorizer"]
    tfidf_matrix = content_model["tfidf_matrix"]
    metadata = content_model["metadata"]

    # Check whether the item exists
    if item_id not in metadata["item_id"].values:
        return pd.DataFrame(
            columns=["item_id", "product_title", "similarity"]
        )

    # Get the item's index
    item_index = metadata.index[
        metadata["item_id"] == item_id
    ][0]

    # Find similar items
    distances, indices = model.kneighbors(
        tfidf_matrix[item_index],
        n_neighbors=top_n + 1
    )

    # Remove the item itself
    similar_indices = indices[0][1:]
    similar_distances = distances[0][1:]

    # Convert cosine distance to cosine similarity
    similarities = 1 - similar_distances

    recommendations = metadata.iloc[
        similar_indices
    ][["item_id", "product_title"]].copy()

    recommendations["similarity"] = similarities

    return recommendations.reset_index(drop=True)

def recommend_items_content_based(
    content_model,
    train_ratings_df,
    user_id,
    top_n=10,
    n_neighbors=20
):
    metadata = content_model["metadata"]

    # Check whether the user exists
    if user_id not in train_ratings_df["user_id"].values:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Get the user's rating history
    user_ratings = train_ratings_df[
        train_ratings_df["user_id"] == user_id
    ][["item_id", "rating"]]

    if user_ratings.empty:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Items already rated by the user
    user_rated_items = set(user_ratings["item_id"])

    recommendation_scores = {}

    # Process each item the user has rated
    for _, row in user_ratings.iterrows():

        rated_item = row["item_id"]
        user_rating = row["rating"]

        if rated_item not in metadata["item_id"].values:
            continue

        # Find similar items
        similar_items = recommend_similar_items(
            content_model,
            rated_item,
            top_n=n_neighbors
        )

        if similar_items.empty:
            continue

        # Calculate weighted recommendation score
        for _, similar_item in similar_items.iterrows():

            item_id = similar_item["item_id"]
            similarity = similar_item["similarity"]

            # Do not recommend already-rated items
            if item_id in user_rated_items:
                continue

            score = similarity * user_rating

            recommendation_scores[item_id] = (
                recommendation_scores.get(item_id, 0)
                + score
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
        .sort_values("score", ascending=False)
        .head(top_n)
    )

    # Add product titles
    recommendations = recommendations.merge(
        metadata[["item_id", "product_title"]],
        on="item_id",
        how="left"
    )

    return recommendations[
        ["item_id", "product_title", "score"]
    ].reset_index(drop=True)

def evaluate_content_based_precision_at_10(
    content_model,
    train_ratings_df,
    test_ratings_df,
    sample_users=100
):
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

        recommendations = recommend_items_content_based(
            content_model,
            train_ratings_df,
            user_id=user_id,
            top_n=10
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
        "Model": "Content-Based",
        "Precision@10": np.mean(precisions),
        "Evaluated Users": evaluated_users
    }
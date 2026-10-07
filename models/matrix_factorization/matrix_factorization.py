import numpy as np
import pandas as pd

from surprise import Dataset, Reader, SVD


def build_svd_model(
    train_ratings_df,
    n_factors=50,
    n_epochs=20,
    lr_all=0.005,
    reg_all=0.02,
    random_state=42
):
    """
    Train an SVD-based collaborative filtering model.

    Parameters
    ----------
    train_ratings_df : pandas.DataFrame
        Training ratings containing:
        user_id, item_id, rating

    n_factors : int
        Number of latent factors.

    n_epochs : int
        Number of training iterations.

    lr_all : float
        Learning rate for optimization.

    reg_all : float
        Regularization parameter.

    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    model : surprise.SVD
        Trained SVD model.
    """

    ratings = train_ratings_df[
        ["user_id", "item_id", "rating"]
    ].copy()

    reader = Reader(
        rating_scale=(
            ratings["rating"].min(),
            ratings["rating"].max()
        )
    )

    dataset = Dataset.load_from_df(
        ratings,
        reader
    )

    trainset = dataset.build_full_trainset()

    model = SVD(
        n_factors=n_factors,
        n_epochs=n_epochs,
        lr_all=lr_all,
        reg_all=reg_all,
        random_state=random_state
    )

    model.fit(trainset)

    return model

def predict_rating_svd(
    svd_model,
    user_id,
    item_id
):
    """
    Predict the rating for a user-item pair.

    Parameters
    ----------
    svd_model : surprise.SVD
        Trained SVD model.

    user_id : str
        User identifier.

    item_id : str
        Item identifier.

    Returns
    -------
    float
        Predicted rating.
    """

    prediction = svd_model.predict(
        user_id,
        item_id
    )

    return float(prediction.est)

def evaluate_svd(
    svd_model,
    test_ratings_df,
    sample_size=500
):
    """
    Evaluate the SVD model using RMSE and MAE.
    """

    from sklearn.metrics import mean_squared_error, mean_absolute_error

    # Select a sample from the test data
    sample = test_ratings_df.sample(
        n=min(sample_size, len(test_ratings_df)),
        random_state=42
    )

    y_true = []
    y_pred = []

    # Predict each user-item pair
    for _, row in sample.iterrows():

        prediction = svd_model.predict(
            row["user_id"],
            row["item_id"]
        )

        y_true.append(row["rating"])
        y_pred.append(prediction.est)

    # Calculate metrics
    rmse = np.sqrt(
        mean_squared_error(y_true, y_pred)
    )

    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    return {
        "Model": "SVD",
        "RMSE": rmse,
        "MAE": mae,
        "Evaluated Samples": len(y_true)
    }

def recommend_items_svd(
    svd_model,
    train_ratings_df,
    metadata_df,
    user_id,
    top_n=10
):
    """
    Generate Top-N item recommendations for a user
    using the SVD model.
    """

    # Check whether the user exists
    if user_id not in train_ratings_df["user_id"].values:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Items the user has already rated
    user_rated_items = set(
        train_ratings_df.loc[
            train_ratings_df["user_id"] == user_id,
            "item_id"
        ]
    )

    # Candidate items
    candidate_items = metadata_df[
        ~metadata_df["item_id"].isin(user_rated_items)
    ][["item_id", "product_title"]].copy()

    if candidate_items.empty:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Predict ratings for candidate items
    predictions = []

    for item_id in candidate_items["item_id"]:
        prediction = svd_model.predict(
            user_id,
            item_id
        )

        predictions.append(prediction.est)

    candidate_items["score"] = predictions

    # Select highest predicted ratings
    recommendations = (
        candidate_items
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return recommendations[
        ["item_id", "product_title", "score"]
    ]

def evaluate_svd_precision_at_10(
    svd_model,
    train_ratings_df,
    test_ratings_df,
    metadata_df,
    sample_users=100
):
    """
    Evaluate SVD recommendations using Precision@10.
    """

    # Users available in the test set
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

        # Generate Top-10 recommendations
        recommendations = recommend_items_svd(
            svd_model,
            train_ratings_df,
            metadata_df,
            user_id=user_id,
            top_n=10
        )

        if recommendations.empty:
            continue

        recommended_items = recommendations["item_id"].tolist()

        # Count relevant recommendations
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
        "Model": "SVD",
        "Precision@10": np.mean(precisions),
        "Evaluated Users": evaluated_users
    }

from surprise import NMF

def build_nmf_model(
    train_ratings_df,
    n_factors=50,
    n_epochs=20,
    reg_pu=0.06,
    reg_qi=0.06,
    random_state=42
):
    """
    Train an NMF-based collaborative filtering model.

    Parameters
    ----------
    train_ratings_df : pandas.DataFrame
        Training ratings containing:
        user_id, item_id, rating

    n_factors : int
        Number of latent factors.

    n_epochs : int
        Number of training iterations.

    reg_pu : float
        Regularization for user factors.

    reg_qi : float
        Regularization for item factors.

    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    model : surprise.NMF
        Trained NMF model.
    """

    ratings = train_ratings_df[
        ["user_id", "item_id", "rating"]
    ].copy()

    reader = Reader(
        rating_scale=(
            ratings["rating"].min(),
            ratings["rating"].max()
        )
    )

    dataset = Dataset.load_from_df(
        ratings,
        reader
    )

    trainset = dataset.build_full_trainset()

    model = NMF(
        n_factors=n_factors,
        n_epochs=n_epochs,
        reg_pu=reg_pu,
        reg_qi=reg_qi,
        random_state=random_state
    )

    model.fit(trainset)

    return model

def predict_rating_nmf(
    nmf_model,
    user_id,
    item_id
):
    """
    Predict the rating for a user-item pair using NMF.
    """

    prediction = nmf_model.predict(
        user_id,
        item_id
    )

    return float(prediction.est)

def evaluate_nmf(
    nmf_model,
    test_ratings_df,
    sample_size=500
):
    """
    Evaluate the NMF model using RMSE and MAE.
    """

    from sklearn.metrics import mean_squared_error, mean_absolute_error

    sample = test_ratings_df.sample(
        n=min(sample_size, len(test_ratings_df)),
        random_state=42
    )

    y_true = []
    y_pred = []

    for _, row in sample.iterrows():

        prediction = nmf_model.predict(
            row["user_id"],
            row["item_id"]
        )

        y_true.append(row["rating"])
        y_pred.append(prediction.est)

    rmse = np.sqrt(
        mean_squared_error(y_true, y_pred)
    )

    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    return {
        "Model": "NMF",
        "RMSE": rmse,
        "MAE": mae,
        "Evaluated Samples": len(y_true)
    }

def recommend_items_nmf(
    nmf_model,
    train_ratings_df,
    metadata_df,
    user_id,
    top_n=10
):
    """
    Generate Top-N item recommendations for a user
    using the NMF model.
    """

    # Check whether the user exists
    if user_id not in train_ratings_df["user_id"].values:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Items already rated by the user
    user_rated_items = set(
        train_ratings_df.loc[
            train_ratings_df["user_id"] == user_id,
            "item_id"
        ]
    )

    # Candidate items = items not rated by the user
    candidate_items = metadata_df[
        ~metadata_df["item_id"].isin(user_rated_items)
    ][["item_id", "product_title"]].copy()

    if candidate_items.empty:
        return pd.DataFrame(
            columns=["item_id", "product_title", "score"]
        )

    # Predict ratings for candidate items
    predictions = []

    for item_id in candidate_items["item_id"]:

        prediction = nmf_model.predict(
            user_id,
            item_id
        )

        predictions.append(prediction.est)

    candidate_items["score"] = predictions

    # Select highest predicted ratings
    recommendations = (
        candidate_items
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return recommendations[
        ["item_id", "product_title", "score"]
    ]

def evaluate_nmf_precision_at_10(
    nmf_model,
    train_ratings_df,
    test_ratings_df,
    metadata_df,
    sample_users=100
):
    """
    Evaluate NMF recommendations using Precision@10.
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

        # Generate Top-10 recommendations
        recommendations = recommend_items_nmf(
            nmf_model,
            train_ratings_df,
            metadata_df,
            user_id=user_id,
            top_n=10
        )

        if recommendations.empty:
            continue

        recommended_items = recommendations["item_id"].tolist()

        # Count recommendation hits
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
        "Model": "NMF",
        "Precision@10": np.mean(precisions),
        "Evaluated Users": evaluated_users
    }
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"


# ============================================================
# MODEL DIRECTORIES
# ============================================================

MODELS_DIR = PROJECT_ROOT / "models"

CF_MODELS_DIR = MODELS_DIR / "collaborative_filtering"
MF_MODELS_DIR = MODELS_DIR / "matrix_factorization"
CONTENT_MODELS_DIR = MODELS_DIR / "content_based"
HYBRID_MODELS_DIR = MODELS_DIR / "hybrid"


# ============================================================
# REPORT DIRECTORIES
# ============================================================

REPORTS_DIR = PROJECT_ROOT / "reports"

EDA_REPORTS_DIR = REPORTS_DIR / "eda"
FIGURES_DIR = REPORTS_DIR / "figures"
MODEL_RESULTS_DIR = REPORTS_DIR / "model_results"


# ============================================================
# DATASET FILES
# ============================================================

GAMES_RATINGS_FILE = PROCESSED_DATA_DIR / "games_clean_ratings.parquet"
GAMES_META_FILE = PROCESSED_DATA_DIR / "games_clean_meta.parquet"
GAMES_TRAIN_FILE = PROCESSED_DATA_DIR / "games_train.parquet"
GAMES_TEST_FILE = PROCESSED_DATA_DIR / "games_test.parquet"

MOVIES_RATINGS_FILE = PROCESSED_DATA_DIR / "movies_clean_ratings.parquet"
MOVIES_META_FILE = PROCESSED_DATA_DIR / "movies_clean_meta.parquet"
MOVIES_TRAIN_FILE = PROCESSED_DATA_DIR / "movies_train.parquet"
MOVIES_TEST_FILE = PROCESSED_DATA_DIR / "movies_test.parquet"


# ============================================================
# RECOMMENDATION SETTINGS
# ============================================================

TOP_N = 10

CF_N_NEIGHBORS = 100

PRECISION_K = 10

RELEVANCE_THRESHOLD = 4


# ============================================================
# RANDOM STATE
# ============================================================

RANDOM_STATE = 42
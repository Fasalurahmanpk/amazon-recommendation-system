from huggingface_hub import snapshot_download
from pathlib import Path
import shutil


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

GAMES_DIR = RAW_DIR / "games"
MOVIES_DIR = RAW_DIR / "movies"

GAMES_DIR.mkdir(parents=True, exist_ok=True)
MOVIES_DIR.mkdir(parents=True, exist_ok=True)


# Download Games files
print("Downloading Video Games dataset...")

games_path = snapshot_download(
    repo_id="McAuley-Lab/Amazon-Reviews-2023",
    repo_type="dataset",
    allow_patterns=[
        "raw/review_categories/Video_Games.jsonl",
        "raw/meta_categories/meta_Video_Games.jsonl",
    ],
    local_dir=str(RAW_DIR / "_hf")
)

print("Games dataset downloaded.")


# Download Movies & TV files
print("Downloading Movies & TV dataset...")

movies_path = snapshot_download(
    repo_id="McAuley-Lab/Amazon-Reviews-2023",
    repo_type="dataset",
    allow_patterns=[
        "raw/review_categories/Movies_and_TV.jsonl",
        "raw/meta_categories/meta_Movies_and_TV.jsonl",
    ],
    local_dir=str(RAW_DIR / "_hf")
)

print("Movies dataset downloaded.")


# Move files to our project structure
hf_dir = RAW_DIR / "_hf" / "raw"

shutil.copy2(
    hf_dir / "review_categories" / "Video_Games.jsonl",
    GAMES_DIR / "Video_Games.jsonl"
)

shutil.copy2(
    hf_dir / "meta_categories" / "meta_Video_Games.jsonl",
    GAMES_DIR / "meta_Video_Games.jsonl"
)

shutil.copy2(
    hf_dir / "review_categories" / "Movies_and_TV.jsonl",
    MOVIES_DIR / "Movies_and_TV.jsonl"
)

shutil.copy2(
    hf_dir / "meta_categories" / "meta_Movies_and_TV.jsonl",
    MOVIES_DIR / "meta_Movies_and_TV.jsonl"
)

print("\nDataset setup completed!")
print(f"Games files  : {GAMES_DIR}")
print(f"Movies files : {MOVIES_DIR}")
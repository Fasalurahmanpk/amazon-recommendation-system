from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


files = {
    "Games Reviews": RAW_DIR / "games" / "Video_Games.jsonl",
    "Games Metadata": RAW_DIR / "games" / "meta_Video_Games.jsonl",
    "Movies Reviews": RAW_DIR / "movies" / "Movies_and_TV.jsonl",
    "Movies Metadata": RAW_DIR / "movies" / "meta_Movies_and_TV.jsonl",
}


def verify_jsonl(name, path):
    print(f"\n{name}")
    print("-" * 50)

    if not path.exists():
        print("❌ File not found")
        return

    print(f"File: {path}")
    print(f"Size: {path.stat().st_size / (1024**3):.2f} GB")

    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline()

    try:
        record = json.loads(first_line)

        print("✓ Valid JSONL")
        print(f"Columns: {list(record.keys())}")
        print(f"Sample record: {record}")

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")


print("=" * 60)
print("AMAZON REVIEWS 2023 - RAW DATA VERIFICATION")
print("=" * 60)

for name, path in files.items():
    verify_jsonl(name, path)

print("\n" + "=" * 60)
print("Verification completed.")
print("=" * 60)
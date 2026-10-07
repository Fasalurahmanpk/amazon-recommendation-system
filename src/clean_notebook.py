from pathlib import Path
import nbformat


def remove_duplicate_cells(notebook_path):
    notebook_path = Path(notebook_path)

    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = nbformat.read(f, as_version=4)

    seen = set()
    unique_cells = []
    duplicates_removed = 0

    for cell in notebook.cells:
        # Use cell type + source so code and markdown
        # with identical text are still treated separately.
        cell_key = (
            cell.cell_type,
            cell.source
        )

        if cell_key in seen:
            duplicates_removed += 1
            continue

        seen.add(cell_key)
        unique_cells.append(cell)

    notebook.cells = unique_cells

    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(notebook, f)

    print(f"\nNotebook: {notebook_path}")
    print(f"Original cells : {len(seen) + duplicates_removed}")
    print(f"Final cells    : {len(unique_cells)}")
    print(f"Duplicates removed: {duplicates_removed}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    notebooks = [
         project_root / "notebook" / "notebooks" / "Eda.ipynb",
    ]

    for notebook in notebooks:
        if notebook.exists():
            remove_duplicate_cells(notebook)
        else:
            print(f"Not found: {notebook}")
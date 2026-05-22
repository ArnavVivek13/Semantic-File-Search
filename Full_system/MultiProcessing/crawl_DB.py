from pathlib import Path
import sqlite3
import time
import concurrent.futures
import os
import pymupdf

from pdf_extractor import pdf_extractor, txt_extractor, docx_extractor
from image_extractor import img_extractor

# -------------------------------------------------
# START TIMER
# -------------------------------------------------

t1 = time.time()

# -------------------------------------------------
# ROOT FOLDER
# -------------------------------------------------

folder_path = Path.home()

SKIP_DIRS = {
    "node_modules",
    ".git",
    "venv",
    "__pycache__",
    "AppData",
    "cache",
    "Caches",
    "drawable",
    "mipmap"
}

BAD_IMAGE_KEYWORDS = {
    "icon",
    "logo",
    "sprite",
    "btn",
    "button",
    "background",
    "bg",
    "thumbnail",
    "thumb",
    "favicon",
    "notification",
    "checkbox",
    "radio",
    "spinner",
    "abc_",
    "mtrl"
}

# -------------------------------------------------
# EXTRACTOR REGISTRY
# -------------------------------------------------

CPU_EXTRACTORS = {
    ".pdf": pdf_extractor,
    ".txt": txt_extractor,
    ".docx": docx_extractor,
}

GPU_EXTRACTORS = {
    ".png": img_extractor,
    ".jpg": img_extractor,
    ".jpeg": img_extractor,
}

ALL_EXTRACTORS = {
    **CPU_EXTRACTORS,
    **GPU_EXTRACTORS
}

# -------------------------------------------------
# DISPATCHER
# -------------------------------------------------

def match_processing(file_path):

    suffix = file_path.suffix.lower()

    extractor = ALL_EXTRACTORS.get(suffix)

    if extractor is None:
        return []

    return extractor(file_path)

# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":

    files = []

    # -------------------------------------------------
    # COLLECT FILES
    # -------------------------------------------------

    for file in folder_path.rglob("*"):

        try:

            if not file.is_file():
                continue

            suffix = file.suffix.lower()

            # -------------------------------------------------
            # SKIP DIRECTORIES
            # -------------------------------------------------

            if any(part in SKIP_DIRS for part in file.parts):
                continue

            # -------------------------------------------------
            # SKIP BAD IMAGE FILENAMES
            # -------------------------------------------------

            if suffix in GPU_EXTRACTORS:

                file_name_lower = file.name.lower()

                if any(keyword in file_name_lower for keyword in BAD_IMAGE_KEYWORDS):
                    print(f"Skipping junk image: {file.name}")
                    continue

            if suffix not in ALL_EXTRACTORS:
                continue

            # Skip empty files
            if file.stat().st_size == 0:
                print(f"Skipping empty file: {file.name}")
                continue

            files.append(file)

        except Exception as e:

            print(f"Failed collecting {file} -> {e}")

    print(f"Total files found: {len(files)}")

    # -------------------------------------------------
    # SPLIT FILES
    # -------------------------------------------------

    cpu_files = []
    gpu_files = []

    for file in files:

        suffix = file.suffix.lower()

        if suffix in CPU_EXTRACTORS:
            cpu_files.append(file)

        elif suffix in GPU_EXTRACTORS:
            gpu_files.append(file)

    print(f"CPU files: {len(cpu_files)}")

    print(f"GPU files: {len(gpu_files)}")

    # -------------------------------------------------
    # RESULTS
    # -------------------------------------------------

    all_results = []

    # -------------------------------------------------
    # CPU MULTIPROCESSING
    # -------------------------------------------------

    print("\nStarting CPU extraction...\n")

    with concurrent.futures.ProcessPoolExecutor(max_workers=max(2, os.cpu_count() // 2)) as executor:

        futures = []

        for file in cpu_files:

            future = executor.submit(
                match_processing,
                file
            )

            futures.append(future)

        for future in concurrent.futures.as_completed(futures):

            try:

                result = future.result()

                if result:
                    all_results.extend(result)

            except Exception as e:

                print(f"CPU worker failed -> {e}")

    # -------------------------------------------------
    # GPU / OLLAMA SEQUENTIAL
    # -------------------------------------------------

    print("\nStarting GPU extraction...\n")

    for file in gpu_files:

        try:

            result = match_processing(file)

            if result:
                all_results.extend(result)

        except Exception as e:

            print(f"GPU extraction failed -> {e}")

    # -------------------------------------------------
    # CHECK EMPTY
    # -------------------------------------------------

    if not all_results:

        print("No results extracted.")

        exit()

    # -------------------------------------------------
    # SQLITE
    # -------------------------------------------------

    conn = sqlite3.connect("Semantic_index.db")

    c = conn.cursor()

    # -------------------------------------------------
    # CREATE TABLE
    # -------------------------------------------------

    c.execute("""
    CREATE TABLE IF NOT EXISTS File_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        File_name TEXT,
        File_location TEXT,
        Page_number INTEGER,
        Chunk_number INTEGER,
        FAISS_idx INTEGER
    )
    """)

    # -------------------------------------------------
    # CREATE INDEX
    # -------------------------------------------------

    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_faiss
    ON File_store(FAISS_idx)
    """)

    # -------------------------------------------------
    # PREPARE ROWS
    # -------------------------------------------------

    db_rows = [
        (
            r[0], # File_name
            r[1], # File_location
            r[2], # Page_number
            r[3], # Chunk_number
            r[4]  # FAISS_idx
        )
        for r in all_results
    ]

    # -------------------------------------------------
    # INSERT
    # -------------------------------------------------

    c.executemany("""
    INSERT INTO File_store (
        File_name,
        File_location,
        Page_number,
        Chunk_number,
        FAISS_idx
    )
    VALUES (?, ?, ?, ?, ?)
    """, db_rows)

    conn.commit()

    conn.close()

    t2 = time.time()

    print(
        f"\nFinished SQLite insertion in {t2 - t1:.2f} seconds"
    )

    # -------------------------------------------------
    # EMBEDDINGS
    # -------------------------------------------------

    print("\nStarting embeddings...\n")

    from FAISS import encode_text, create_index

    rich_texts = [r[5] for r in all_results]
    ids = [r[4] for r in all_results]
    vectors = encode_text(rich_texts)
    t3 = time.time()
    print(
        f"\nFinished embeddings in {t3 - t2:.2f} seconds"
    )

    # -------------------------------------------------
    # FAISS
    # -------------------------------------------------
    print("\nCreating FAISS index...\n")
    index = create_index(vectors, ids)
    t4 = time.time()
    print(
        f"\nFinished FAISS indexing in {t4 - t3:.2f} seconds"
    )
    # -------------------------------------------------
    # TOTAL
    # -------------------------------------------------
    print(
        f"\nTOTAL TIME: {t4 - t1:.2f} seconds"
    )
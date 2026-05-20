import pymupdf
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sqlite3
import time

t1 = time.time()
folder_path = Path.home()

# SQLite connection
conn = sqlite3.connect("Semantic_index.db")

c = conn.cursor()

# Create table
c.execute("""
CREATE TABLE IF NOT EXISTS File_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    File_name TEXT,
    File_location TEXT,
    Page_number INTEGER,
    Chunk_number INTEGER,
    FAISS_idx INTEGER
)
""")

# Text splitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

texts = []

faiss_counter = 0

for pdf_file in folder_path.rglob("*.pdf"):

    # Skip empty files
    if pdf_file.stat().st_size == 0:
        print(f"Skipping empty file: {pdf_file.name}")
        continue

    try:

        doc = pymupdf.open(pdf_file)

        # Skip empty PDFs
        if doc.page_count == 0:
            print(f"Skipping PDF with 0 pages: {pdf_file.name}")
            doc.close()
            continue

        print(f"Processing: {pdf_file.name}")

        file_name = pdf_file.name

        file_location = str(pdf_file.resolve())

        folder_name = pdf_file.parent.name

        for page_num in range(doc.page_count):

            page = doc.load_page(page_num)

            text = page.get_text().strip()

            if not text:
                continue

            # --------------------------------
            # CHUNK PAGE TEXT
            # --------------------------------
            chunks = splitter.split_text(text)

            for chunk_num, chunk in enumerate(chunks):

                # --------------------------------
                # METADATA ENRICHMENT
                # --------------------------------
                rich_text = f"""
Filename: {file_name}

Folder: {folder_name}

File Path: {file_location}

Page Number: {page_num}

Chunk Number: {chunk_num}

Content:
{chunk}
"""

                texts.append(rich_text)

                # Insert metadata
                c.execute("""
                INSERT INTO File_info (
                    File_name,
                    File_location,
                    Page_number,
                    Chunk_number,
                    FAISS_idx
                )
                VALUES (?, ?, ?, ?, ?)
                """, (
                    file_name,
                    file_location,
                    page_num,
                    chunk_num,
                    faiss_counter
                ))

                faiss_counter += 1

        doc.close()

    except Exception as e:

        print(f"Failed: {pdf_file.name} -> {e}")

# Save DB
conn.commit()

conn.close()

print("Done indexing PDFs into SQLite.")

t2 = time.time()

print(t2 - t1)
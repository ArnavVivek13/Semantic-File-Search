import pymupdf
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sqlite3
import time
import concurrent.futures
import os
import uuid

t1 = time.time()
folder_path = Path.home()

# Text splitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

def process_pdf(pdf_file):
    try:
        results = []
        doc = pymupdf.open(pdf_file)

        # Skip empty PDFs
        if doc.page_count == 0:
            print(f"Skipping PDF with 0 pages: {pdf_file.name}")
            doc.close()
            return []

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
                unique_id = uuid.uuid4()
                faiss_id = unique_id.int & ((1 << 63) - 1)
                results.append((
                            file_name, # 0
                            file_location, # 1
                            page_num, # 2
                            chunk_num, # 3
                            faiss_id, # 4
                            rich_text # 5
                        ))

        doc.close()
        return results

    except Exception as e:
        print(f"Failed: {pdf_file.name} -> {e}")
        return []

if __name__ == "__main__":

    pdf_files = [] # Stores paths of all the pdfs for now

    for pdf_file in folder_path.rglob("*.pdf"):

        # Skip empty files
        if pdf_file.stat().st_size == 0:
            print(f"Skipping empty file: {pdf_file.name}")
            continue

        pdf_files.append(pdf_file)

    all_results = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:

        futures = []

        for pdf_file in pdf_files:
            future = executor.submit(process_pdf, pdf_file)
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):

            result = future.result()

            if result:
                all_results.extend(result)

    # SQLite connection
    conn = sqlite3.connect("Semantic_index.db")

    c = conn.cursor()

    # Create table
    c.execute("""
    CREATE TABLE IF NOT EXISTS PDF_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        File_name TEXT,
        File_location TEXT,
        Page_number INTEGER,
        Chunk_number INTEGER,
        FAISS_idx INTEGER
    )
    """)

    db_rows = [
        (r[0], r[1], r[2], r[3], r[4])
        for r in all_results
    ]

    c.executemany("""
    INSERT INTO PDF_store (
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
    print(f"Finished adding the files to SQLite Database in {t2 - t1} seconds")

    from FAISS import encode_text, create_index
    rich_texts = [r[5] for r in all_results]

    ids = [r[4] for r in all_results]

    vectors = encode_text(rich_texts)

    t3 = time.time()

    print(f"Finished encoding the rich texts in {t3-t2} seconds")

    index = create_index(vectors, ids)

    t4 = time.time()

    print(f"Finished creating FAISS Index in {t4-t3} seconds")
from pathlib import Path
import sqlite3
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf
import queue

def process_pdfs(batch, DB_queue, Chunk_queue):    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    for file_path, _ in batch:
        if file_path.stat().st_size == 0:
            print(f"Skipping empty file: {file_path.name}")
            continue

        try:

            doc = pymupdf.open(file_path)

            # Skip empty PDFs
            if doc.page_count == 0:
                print(f"Skipping PDF with 0 pages: {file_path.name}")
                doc.close()
                continue

            print(f"Processing: {file_path.name}")
            file_name = file_path.name
            file_location = str(file_path.resolve())
            folder_name = file_path.parent.name
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
                    # Chunk_queue.put({
                    #     "text": rich_text,
                    #     "file_name": file_name,
                    #     "path": file_location,
                    #     "page": page_num,
                    #     "chunk": chunk_num
                    # })
                    DB_queue.put((
                        file_name,
                        file_location,
                        page_num,
                        chunk_num
                    ))

            doc.close()

        except Exception as e:
            print(f"Failed: {file_path.name} -> {e}")

def create_index_pdf(text):
    print("Making FAISS index...")
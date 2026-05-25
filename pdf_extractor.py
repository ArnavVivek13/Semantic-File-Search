import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
import uuid
from docx import Document

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

def pdf_extractor(pdf_file):
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
                File Type: PDF
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
                            page_num+1, # 2
                            chunk_num, # 3
                            faiss_id, # 4
                            rich_text # 5
                        ))

        doc.close()
        return results

    except Exception as e:
        print(f"Failed: {pdf_file.name} -> {e}")
        return []


def txt_extractor(txt_file):
    try:
        results = []
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        file_name = txt_file.name
        file_location = str(txt_file.resolve())
        folder_name = txt_file.parent.name

        if not text:
            return []

        # --------------------------------
        # CHUNK TEXT
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
            File Type: txt
            Chunk Number: {chunk_num}
            Content:
            {chunk}
            """
            unique_id = uuid.uuid4()
            faiss_id = unique_id.int & ((1 << 63) - 1)
            results.append((
                        file_name, # 0
                        file_location, # 1
                        -1, # 2
                        chunk_num, # 3
                        faiss_id, # 4
                        rich_text # 5
                    ))

        return results

    except Exception as e:
        print(f"Failed: {txt_file.name} -> {e}")
        return []
    
def docx_extractor(doc_file):
    try:
        results = []
        doc = Document(doc_file)

        print(f"Processing: {doc_file.name}")
        file_name = doc_file.name
        file_location = str(doc_file.resolve())
        folder_name = doc_file.parent.name

        text = "\n".join(
            para.text
            for para in doc.paragraphs
            if para.text.strip()
        )

        if not text.strip():
            print(f"Skipping empty DOCX: {doc_file.name}")
            return []
        
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
            File Type: Docx
            Chunk Number: {chunk_num}
            Content:
            {chunk}
            """
            unique_id = uuid.uuid4()
            faiss_id = unique_id.int & ((1 << 63) - 1)
            results.append((
                        file_name, # 0
                        file_location, # 1
                        -1, # 2
                        chunk_num, # 3
                        faiss_id, # 4
                        rich_text # 5
                    ))

        return results

    except Exception as e:
        print(f"Failed: {doc_file.name} -> {e}")
        return []
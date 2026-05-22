from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path
import torch
import faiss
import sqlite3

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(
    "all-MiniLM-L6-v2",
    device=device
)
print(model.device)

def encode_text(rich_texts):
    embeddings = model.encode(
        rich_texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    print(embeddings.shape)
    vectors = np.array(embeddings).astype("float32")
    return vectors

def create_index(vectors, ids):
    index_path = Path("file.index")

    if index_path.exists():
        index = faiss.read_index("file.index")
    
    else:
        dimension = vectors.shape[1]
        base_index = faiss.IndexFlatIP(dimension)
        index = faiss.IndexIDMap(base_index)

    ids = np.array(ids).astype("int64")
    index.add_with_ids(vectors, ids)

    faiss.write_index(index, "file.index")
    return index

def search_index(query):
    index = faiss.read_index("file.index")

    print("Total vectors:", index.ntotal)

    query_vector = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    # -----------------------------
    # SEARCH FAISS
    # -----------------------------
    D, I = index.search(query_vector, k=200)

    # -----------------------------
    # SQLITE LOOKUP
    # -----------------------------
    conn = sqlite3.connect("Semantic_index.db")
    c = conn.cursor()

    seen_files = set()
    unique_results = []

    for i in range(len(I[0])):

        faiss_idx = int(I[0][i])

        if faiss_idx == -1:
            continue

        similarity_score = float(D[0][i])

        c.execute("""
        SELECT *
        FROM File_store
        WHERE FAISS_idx = ?
        """, (faiss_idx,))

        result = c.fetchone()

        if result is None:
            continue

        file_name = result[1]
        file_location = result[2]
        page_number = result[3]

        # Skip duplicate files
        if file_location in seen_files:
            continue

        seen_files.add(file_location)

        unique_results.append({
            "file_name": file_name,
            "file_location": file_location,
            "page_number": page_number,
            "score": similarity_score
        })

        # Stop at 25 unique files
        if len(unique_results) == 25:
            break

    conn.close()

    # -----------------------------
    # PRINT RESULTS
    # -----------------------------
    for idx, result in enumerate(unique_results):
        print(f"Rank #{idx + 1}")

        print("Similarity:", round(result["score"], 4))

        print("File Name:", result["file_name"])

        print("Location:", result["file_location"])

        print("Page:", result["page_number"])

        print("-" * 50)

    return unique_results
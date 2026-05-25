# Semantic File Search

Semantic File Search is a local semantic search engine for your files. It scans documents and images, converts their contents into embeddings, stores those embeddings in a FAISS index, and uses SQLite to map search results back to the original file path, page number, and chunk.

It is built for searching by meaning rather than exact keywords. For example, a query can find a relevant PDF page, text file section, DOCX paragraph, or image caption even when the exact query words are not present in the filename.

## Features

- Semantic search over local files.
- FAISS vector indexing and similarity search.
- SQLite metadata storage for file paths, page numbers, chunks, and FAISS IDs.
- Multiprocessing document extraction for faster indexing than a single-process pipeline.
- Chunk-level indexing for large documents.
- Page-aware PDF results, so search can point to where information appears inside a document.
- Image search through Ollama-generated captions.
- Junk image filtering using filename keywords and minimum image dimensions.
- UUID-derived FAISS IDs for unique vector-to-metadata mapping.
- CUDA-enabled PyTorch support for faster embeddings when an NVIDIA GPU is available.
- Simple Tkinter UI that shows the top 25 unique search results.

## Supported Files

Currently registered extractors support:

- `.pdf`
- `.txt`
- `.docx`
- `.png`
- `.jpg`
- `.jpeg`

Legacy `.doc` files are not currently registered in the code. Convert them to `.docx`, or add a `.doc` extractor and register it in `CPU_EXTRACTORS` inside `crawl_DB.py`.

## Project Structure

```text
.
├── crawl_DB.py          # Main indexing pipeline
├── FAISS.py             # Embedding, FAISS indexing, and search
├── pdf_extractor.py     # PDF, TXT, and DOCX extraction
├── image_extractor.py   # Image captioning through Ollama/moondream
├── searching.py         # Command-line search
├── display.py           # Tkinter search UI
├── requirements.txt     # Python dependencies
├── Semantic_index.db    # Generated SQLite metadata DB
└── file.index           # Generated FAISS vector index
```

`Semantic_index.db` and `file.index` are generated files and should not be committed.

## Installation

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

This project uses CUDA-enabled PyTorch in `requirements.txt`:

```text
torch==2.11.0+cu128
torchvision==0.26.0+cu128
torchaudio==2.11.0+cu128
```

If PyTorch ever falls back to CPU, reinstall the CUDA wheels:

```powershell
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Check GPU support:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Expected result on an NVIDIA GPU system:

```text
True
12.8
NVIDIA ...
```

## Ollama Setup

Image indexing uses Ollama with the `moondream` vision model.

Install or pull the model:

```powershell
ollama pull moondream
```

Make sure Ollama is running before indexing images.

## Usage

Build or extend the index:

```powershell
python crawl_DB.py
```

Run command-line search:

```powershell
python searching.py
```

Run the UI:

```powershell
python display.py
```

By default, `crawl_DB.py` scans from:

```python
Path.home()
```

Change `folder_path` in `crawl_DB.py` if you want to index a smaller directory.

## How It Works

### 1. File Discovery

`crawl_DB.py` recursively scans the home directory and collects supported files.

It skips:

- Unsupported extensions.
- Empty files.
- Common noisy directories such as `.git`, `venv`, `node_modules`, `__pycache__`, `AppData`, and cache folders.
- Likely junk images with names containing words such as `icon`, `logo`, `sprite`, `thumbnail`, `favicon`, `button`, `spinner`, and similar UI asset terms.

The discovered files are split into:

- CPU files: PDFs, TXT files, and DOCX files.
- Image files: PNG, JPG, and JPEG files processed through Ollama/moondream.

### 2. Multiprocessing Document Extraction

Text-based files are processed with `ProcessPoolExecutor`:

```python
max_workers=max(2, os.cpu_count() // 2)
```

This parallelizes PDF, TXT, and DOCX extraction across multiple worker processes, which makes large indexing runs much faster than processing one file at a time.

Current document extractors:

- `pdf_extractor()` uses PyMuPDF.
- `txt_extractor()` reads UTF-8 text.
- `docx_extractor()` uses `python-docx`.

### 3. Chunking and Location-Aware Metadata

Large text is split with LangChain's `RecursiveCharacterTextSplitter`:

```python
chunk_size = 500
chunk_overlap = 100
```

Each chunk is stored as a separate searchable unit. The system also stores metadata for that chunk:

- File name.
- Full file path.
- Parent folder.
- File type.
- PDF page number, when available.
- Chunk number.
- FAISS vector ID.

This is useful for large documents. Search does not only return the matching file; for PDFs, it can also return the page number where the relevant information was found.

### 4. Image Captioning Pipeline

Images are handled separately from text documents.

`image_extractor.py`:

1. Opens the image with Pillow.
2. Skips images smaller than `128x128`.
3. Sends the image to Ollama using `moondream`.
4. Generates a concise semantic caption.
5. Wraps the caption with file metadata.
6. Sends the caption text into the same embedding/indexing pipeline as documents.

This allows image content to live in the same FAISS search space as text documents.

### 5. Unique FAISS Mapping

Each chunk or image caption gets a UUID-derived 63-bit integer ID:

```python
unique_id = uuid.uuid4()
faiss_id = unique_id.int & ((1 << 63) - 1)
```

That ID is stored in both places:

- FAISS stores it as the vector ID.
- SQLite stores it as `FAISS_idx`.

When FAISS returns similar vectors, SQLite uses the ID to retrieve the original file metadata.

### 6. SQLite Metadata Store

Metadata is stored in `Semantic_index.db`.

The main table is:

```sql
CREATE TABLE IF NOT EXISTS File_store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    File_name TEXT,
    File_location TEXT,
    Page_number INTEGER,
    Chunk_number INTEGER,
    FAISS_idx INTEGER
)
```

An index is created on `FAISS_idx` for faster lookup:

```sql
CREATE INDEX IF NOT EXISTS idx_faiss
ON File_store(FAISS_idx)
```

SQLite stores metadata only. The actual vectors are stored in `file.index`.

### 7. Embeddings

Embeddings are generated in `FAISS.py` with:

```python
SentenceTransformer("all-MiniLM-L6-v2")
```

The code selects GPU automatically when available:

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
```

Embeddings are generated with:

```python
batch_size=64
normalize_embeddings=True
convert_to_numpy=True
```

The vectors are converted to `float32` before FAISS insertion.

### 8. FAISS Indexing

The FAISS index is stored in:

```text
file.index
```

If an index already exists, it is loaded and extended. Otherwise, a new index is created:

```python
base_index = faiss.IndexFlatIP(dimension)
index = faiss.IndexIDMap(base_index)
```

Because embeddings are normalized, inner-product search behaves like cosine similarity.

### 9. Search

Search is handled by `search_index(query)` in `FAISS.py`.

The search process:

1. Load `file.index`.
2. Embed the query with `all-MiniLM-L6-v2`.
3. Search FAISS with `k=200`.
4. Look up each FAISS ID in SQLite.
5. Deduplicate results by file path.
6. Return the top 25 unique files.

Each result contains:

- File name.
- File location.
- PDF page number, when available.
- Similarity score.

## UI

`display.py` provides a small Tkinter interface.

You can:

- Enter a natural-language query.
- Press Enter or click Search.
- View ranked results and similarity scores.
- Double-click a result to reveal the file in Windows File Explorer.

## Rebuilding the Index

Running `crawl_DB.py` again appends new rows and vectors to the existing database and FAISS index.

To rebuild from scratch, delete:

```text
Semantic_index.db
file.index
```

Then run:

```powershell
python crawl_DB.py
```

## Notes

- PDF page numbers are stored as 1-based page numbers.
- TXT, DOCX, and image records use `-1` for page number.
- Image caption quality depends on the local `moondream` model.
- If embeddings run on CPU, verify that the active venv has CUDA-enabled PyTorch installed.

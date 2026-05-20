from pathlib import Path
from Full_system.MultiThread.processing import process_pdfs
import queue
import threading
import sqlite3
import time

t1 = time.time()

SUPPORTED_EXTENSIONS = {
    ".pdf",
}

Q = queue.Queue(maxsize=1000)
Chunk_Queue = queue.Queue(maxsize=1000)
DB_queue = queue.Queue(maxsize=1000)

BATCH_SIZE = 32
NUM_WORKERS = 4

def process_file_batch(batch):
    process_pdfs(batch, DB_queue, Chunk_Queue)

def crawl_drive(drive_path):
    stack = [drive_path]

    while stack:
        current_path = stack.pop()
        try:
            for entry in current_path.iterdir():
                try: 
                    if entry.is_dir():
                        stack.append(entry)
                    elif entry.is_file():
                        extension = entry.suffix.lower()
                        
                        if extension in SUPPORTED_EXTENSIONS:
                            Q.put((entry, extension))
                except Exception as e:
                    print(f"Failed to process file: {entry} -> {e}")

        except Exception as e:
            print(f"Cannot access path: {current_path} -> {e}")

def worker():
    batch = []

    while True:
        try:
            item = Q.get(timeout=2)

            # Shutdown signal
            if item is None:
                if batch:
                    process_file_batch(batch)

                    for _ in batch:
                        Q.task_done()
                    batch.clear()
                
                Q.task_done()
                break

            batch.append(item)

            # Batch full
            if len(batch) >= BATCH_SIZE:
                process_file_batch(batch)

                for _ in batch:
                    Q.task_done()

                batch.clear()

        except queue.Empty:
            # Process partial batch
            if batch:
                process_file_batch(batch)

                for _ in batch:
                    Q.task_done()

                batch.clear()

def db_writer_pdf():
    conn = sqlite3.connect("Semantic_Index.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS PDF_Store(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        File_name TEXT,
        File_location TEXT,
        Page_number INTEGER,
        Chunk_number INTEGER
    )
    """)

    conn.commit()

    batch = []
    DB_BATCH_SIZE = 100

    while True:
        try:
            item = DB_queue.get(timeout=2)

            # Shutdown signal
            if item is None:
                if batch:
                    c.executemany("""
                    INSERT INTO PDF_Store (
                        File_name,
                        File_location,
                        Page_number,
                        Chunk_number
                    )
                    VALUES (?, ?, ?, ?)
                    """, batch)

                    conn.commit()

                    for _ in batch:
                        DB_queue.task_done()

                    batch.clear()

                DB_queue.task_done()
                break

            batch.append(item)

            # Batch full
            if len(batch) >= DB_BATCH_SIZE:
                c.executemany("""
                INSERT INTO PDF_Store (
                    File_name,
                    File_location,
                    Page_number,
                    Chunk_number
                )
                VALUES (?, ?, ?, ?)
                """, batch)

                conn.commit()

                for _ in batch:
                    DB_queue.task_done()

                batch.clear()

        except queue.Empty:
            # Flush partial batch
            if batch:
                c.executemany("""
                INSERT INTO PDF_Store (
                    File_name,
                    File_location,
                    Page_number,
                    Chunk_number
                )
                VALUES (?, ?, ?, ?)
                """, batch)

                conn.commit()

                for _ in batch:
                    DB_queue.task_done()

                batch.clear()

    conn.close()

    print("DB writer stopped.")


PATH = Path.home()
crawler_thread = threading.Thread(target=crawl_drive, args=[PATH])
db_thread = threading.Thread(target=db_writer_pdf)

workers = []
for _ in range(NUM_WORKERS):
    t = threading.Thread(target=worker)
    t.start()
    workers.append(t)

db_thread.start()
crawler_thread.start()

crawler_thread.join()
for _ in range(NUM_WORKERS):
    Q.put(None)

Q.join()

for t in workers:
    t.join()

DB_queue.put(None)
DB_queue.join()
db_thread.join()

t2 = time.time()

print(t2-t1)
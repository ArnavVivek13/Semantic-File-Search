import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import os
import sys
from FAISS import search_index


class SemanticSearchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Semantic File Search")
        self.root.geometry("1000x700")

        self.results = []
        self.index_process = None

        # -----------------------------
        # SEARCH BAR
        # -----------------------------
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill="x")

        self.query_var = tk.StringVar()

        self.search_entry = ttk.Entry(
            top_frame,
            textvariable=self.query_var,
            font=("Segoe UI", 12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.search_button = ttk.Button(
            top_frame,
            text="Search",
            command=self.perform_search
        )
        self.search_button.pack(side="left")

        self.search_entry.bind("<Return>", lambda e: self.perform_search())

        # -----------------------------
        # INDEX CONTROLS
        # -----------------------------
        index_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        index_frame.pack(fill="x")

        self.index_button = ttk.Button(
            index_frame,
            text="Index all files",
            command=self.start_indexing
        )
        self.index_button.pack(side="left", padx=(0, 10))

        self.loading = ttk.Progressbar(
            index_frame,
            mode="indeterminate",
            length=180
        )
        self.loading.pack(side="left", padx=(0, 10))
        self.loading.pack_forget()

        self.index_status_var = tk.StringVar(value="Ready to search.")
        self.index_status = ttk.Label(
            index_frame,
            textvariable=self.index_status_var
        )
        self.index_status.pack(side="left", fill="x", expand=True)

        # -----------------------------
        # RESULTS LIST
        # -----------------------------
        self.results_frame = ttk.Frame(root, padding=10)
        self.results_frame.pack(fill="both", expand=True)

        self.results_list = tk.Listbox(
            self.results_frame,
            font=("Consolas", 11),
            height=25
        )
        self.results_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            self.results_frame,
            orient="vertical",
            command=self.results_list.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.results_list.config(yscrollcommand=scrollbar.set)

        self.results_list.bind("<Double-Button-1>", self.open_selected_file)

        # -----------------------------
        # INFO LABEL
        # -----------------------------
        self.info_label = ttk.Label(
            root,
            text="Double click a result to open in File Explorer",
            padding=10
        )
        self.info_label.pack()

    def set_search_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.search_entry.config(state=state)
        self.search_button.config(state=state)

    def start_indexing(self):
        if self.index_process is not None:
            return

        script_path = os.path.join(os.path.dirname(__file__), "crawl_DB.py")

        self.results = []
        self.results_list.delete(0, tk.END)
        self.results_list.insert(tk.END, "Indexing all files. Please wait...")

        self.set_search_enabled(False)
        self.index_button.config(state="disabled")
        self.index_status_var.set(
            "Indexing files... Do not close this window until indexing is done."
        )
        self.loading.pack(side="left", padx=(0, 10))
        self.loading.start(10)

        try:
            self.index_process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            self.finish_indexing(success=False, message=f"Failed to start indexing: {e}")
            return

        self.root.after(500, self.check_indexing_status)

    def check_indexing_status(self):
        if self.index_process is None:
            return

        return_code = self.index_process.poll()

        if return_code is None:
            self.root.after(500, self.check_indexing_status)
            return

        success = return_code == 0
        message = (
            "Indexing complete. You can search now."
            if success
            else f"Indexing stopped with exit code {return_code}."
        )
        self.finish_indexing(success=success, message=message)

    def finish_indexing(self, success, message):
        self.index_process = None
        self.loading.stop()
        self.loading.pack_forget()
        self.index_status_var.set(message)
        self.index_button.config(state="normal")
        self.set_search_enabled(True)

        self.results_list.delete(0, tk.END)
        self.results_list.insert(tk.END, message)

    def perform_search(self):
        if self.index_process is not None:
            self.results_list.delete(0, tk.END)
            self.results_list.insert(
                tk.END,
                "Search is disabled while indexing. Do not close until indexing is done."
            )
            return

        query = self.query_var.get().strip()

        if not query:
            return

        self.results_list.delete(0, tk.END)

        try:
            self.results = search_index(query)

            if not self.results:
                self.results_list.insert(tk.END, "No results found.")
                return

            for idx, result in enumerate(self.results):
                display_text = (
                    f"[{idx + 1}] "
                    f"{result['file_name']} "
                    f"| Score: {result['score']:.4f} "
                    f"| Page: {result['page_number']}"
                )

                self.results_list.insert(tk.END, display_text)

        except Exception as e:
            self.results_list.insert(tk.END, f"Error: {e}")

    def open_selected_file(self, event):
        selection = self.results_list.curselection()

        if not selection:
            return

        index = selection[0]

        if index >= len(self.results):
            return

        file_path = self.results[index]["file_location"]

        if not os.path.exists(file_path):
            return

        subprocess.run([
            "explorer",
            "/select,",
            file_path
        ])


if __name__ == "__main__":
    root = tk.Tk()
    app = SemanticSearchUI(root)
    root.mainloop()

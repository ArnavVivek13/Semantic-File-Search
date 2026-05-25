import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import os
from FAISS import search_index


class SemanticSearchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Semantic File Search")
        self.root.geometry("1000x700")

        self.results = []

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

    def perform_search(self):
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

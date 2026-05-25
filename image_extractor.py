from pathlib import Path
import uuid
import ollama
from PIL import Image

def img_extractor(img_path):
    try:
        img = Image.open(img_path)

        if img.width < 128 or img.height < 128:
            print(f"Image: {img_path.name}")
            return []

        results = []

        print(f"Processing: {img_path.name}")
        file_name = img_path.name
        file_location = str(img_path.resolve())
        folder_name = img_path.parent.name

        response = ollama.chat(
            model="moondream",
            messages=[
                {
                    "role": "user",
                    "content": """
        Give a concise semantic description of this image.
        Focus on:
        - important visible text
        - software/tools
        - code concepts
        """,
                    "images": [str(img_path)]
                }
            ],
            options={
                "num_predict": 80
            }
        )
        
        text = response["message"]["content"]
        
        rich_text = f"""
        Filename: {file_name}
        Folder: {folder_name}
        File Path: {file_location}
        File Type: Image
        Caption:{text}
        """

        unique_id = uuid.uuid4()
        faiss_id = unique_id.int & ((1 << 63) - 1)
        results.append((
                    file_name, # 0
                    file_location, # 1
                    -1, # 2
                    -1, # 3
                    faiss_id, # 4
                    rich_text # 5
                ))

        return results

    except Exception as e:
        print(f"Failed: {img_path.name} -> {e}")
        return []
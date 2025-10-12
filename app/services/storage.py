# placeholder for future uploads (e.g., saving to static/uploads)
import os

def save_upload(fileobj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(fileobj.read())
    return path

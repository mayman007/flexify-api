import os
from dotenv import load_dotenv

load_dotenv()

# Define paths to the asset folders
ASSET_PATHS = {
    "wallpapers": {
        "base": os.path.join(os.getenv("WALLPAPERS_BASE_PATH")),
        "subfolders": ["hq", "mid", "low"],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif')
    },
    "widgets": {
        "base": os.path.join(os.getenv("WIDGETS_BASE_PATH")),
        "subfolders": [],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif', '.kwgt')
    },
    "klwp": {
        "base": os.path.join(os.getenv("KLWP_BASE_PATH")),
        "subfolders": [],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif', '.klwp')
    }
}

# Cache files for different asset types
CACHE_FILES = {
    "wallpapers": os.path.join(os.getenv("WALLPAPERS_BASE_PATH"), "metadata.json"),
    "widgets": os.path.join(os.getenv("WIDGETS_BASE_PATH"), "metadata.json"),
    "klwp": os.path.join(os.getenv("KLWP_BASE_PATH"), "metadata.json")
}

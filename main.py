from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict
import os
from PIL import Image
from collections import Counter
from pydantic import BaseModel
import json
import uvicorn

app = FastAPI()

# Define paths to the hq and mid folders
HQ_FOLDER = os.path.join("../flexify_assets/wallpapers", "hq")
MID_FOLDER = os.path.join("../flexify_assets/wallpapers", "mid")
CACHE_FILE = os.path.join("../flexify_assets/wallpapers", "metadata.json")


# Pydantic model for wallpaper metadata
class WallpaperResponse(BaseModel):
    name: str
    category: str
    resolution: str
    size: int
    colors: List[str]


# Cache storage
metadata_cache = {}


def load_cache():
    """Load metadata cache from file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: Dict):
    """Save metadata cache to file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)


def get_prominent_colors(image_path: str, num_colors: int = 5) -> List[str]:
    """Extract prominent colors from an image."""
    try:
        with Image.open(image_path) as img:
            img = img.resize((100, 100))
            img = img.convert("RGB")
            pixels = list(img.getdata())
            color_counts = Counter(pixels).most_common(num_colors)
            colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in color_counts]
            return colors
    except Exception:
        return ["#000000"]


def update_cache():
    """Update the metadata cache to include new or modified files."""
    wallpapers = {}
    for folder, folder_type in [(HQ_FOLDER, "hq"), (MID_FOLDER, "mid")]:
        if not os.path.exists(folder):
            continue

        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder)
                    category = os.path.dirname(relative_path)
                    last_modified = os.path.getmtime(file_path)

                    # Cache key includes folder type for distinction
                    cache_key = f"{folder_type}/{relative_path}"

                    # Check if already cached and up-to-date
                    if cache_key in metadata_cache:
                        cached_data = metadata_cache[cache_key]
                        if cached_data["last_modified"] == last_modified:
                            wallpapers[cache_key] = cached_data
                            continue

                    # Process new or modified file
                    try:
                        size = os.path.getsize(file_path)
                        with Image.open(file_path) as img:
                            resolution = f"{img.width}x{img.height}"
                            colors = get_prominent_colors(file_path)
                    except Exception:
                        resolution = "Unknown"
                        colors = ["#000000"]

                    wallpapers[cache_key] = {
                        "name": file,
                        "category": category,
                        "resolution": resolution,
                        "size": size,
                        "colors": colors,
                        "last_modified": last_modified,
                        "folder_type": folder_type,
                    }

    # Update the cache with the current files
    metadata_cache.update(wallpapers)

    # Remove any files that are no longer present
    cached_files = set(metadata_cache.keys())
    current_files = set(wallpapers.keys())
    for missing_file in cached_files - current_files:
        del metadata_cache[missing_file]

    save_cache(metadata_cache)


@app.on_event("startup")
def on_startup():
    """Load cache and update it on startup."""
    global metadata_cache
    metadata_cache = load_cache()
    update_cache()


@app.get("/wallpapers/{folder_type}", response_model=List[WallpaperResponse])
def list_wallpapers_by_folder(folder_type: str):
    """List wallpapers filtered by folder type ('hq' or 'mid')."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    update_cache()  # Ensure the cache is up-to-date
    filtered_wallpapers = [
        data
        for key, data in metadata_cache.items()
        if data["folder_type"] == folder_type
    ]
    if not filtered_wallpapers:
        raise HTTPException(
            status_code=404,
            detail=f"No wallpapers found in folder '{folder_type}'."
        )
    return filtered_wallpapers


@app.get("/wallpapers/{folder_type}/{category}", response_model=List[WallpaperResponse])
def list_wallpapers_by_category(folder_type: str, category: str):
    """List wallpapers filtered by folder type and category."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    # Determine the absolute path to the category
    folder_path = os.path.abspath(HQ_FOLDER if folder_type == "hq" else MID_FOLDER)
    category_path = os.path.abspath(os.path.join(folder_path, category))

    # Ensure the category path exists and is within the folder_path
    if not category_path.startswith(folder_path) or not os.path.isdir(category_path):
        raise HTTPException(status_code=404, detail="Category not found.")

    # Update cache to ensure it's up-to-date
    update_cache()

    # Filter wallpapers by category
    filtered_wallpapers = [
        data
        for key, data in metadata_cache.items()
        if data["folder_type"] == folder_type and data["category"] == category
    ]

    if not filtered_wallpapers:
        raise HTTPException(
            status_code=404,
            detail=f"No wallpapers found in category '{category}'."
        )

    return filtered_wallpapers

@app.get("/wallpapers/{folder_type}/{category}/{filename}")
def get_wallpaper_file(folder_type: str, category: str, filename: str):
    """Serve the actual wallpaper file."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    folder_path = HQ_FOLDER if folder_type == "hq" else MID_FOLDER
    category_path = os.path.join(folder_path, category)
    file_path = os.path.join(category_path, filename)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

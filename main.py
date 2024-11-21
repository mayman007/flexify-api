from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict, Literal, Union
import os
from PIL import Image
from collections import Counter
from pydantic import BaseModel
import json
import uvicorn

app = FastAPI()

# Define paths to the asset folders
ASSET_PATHS = {
    "wallpapers": {
        "base": os.path.join("../flexify_assets/wallpapers"),
        "subfolders": ["hq", "mid"],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif')
    },
    "widgets": {
        "base": os.path.join("../flexify_assets/widgets"),
        "subfolders": [],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif', '.kwgt')
    },
    "klwp": {
        "base": os.path.join("../flexify_assets/klwp"),
        "subfolders": [],
        "file_types": ('.png', '.jpg', '.jpeg', '.gif', '.klwp')
    }
}

# Cache files for different asset types
CACHE_FILES = {
    "wallpapers": os.path.join("../flexify_assets/wallpapers", "metadata.json"),
    "widgets": os.path.join("../flexify_assets/widgets", "metadata.json"),
    "klwp": os.path.join("../flexify_assets/klwp", "metadata.json")
}

# Pydantic models for different asset types
class WallpaperResponse(BaseModel):
    name: str
    category: str
    resolution: str
    size: int
    colors: List[str]

class WidgetResponse(BaseModel):
    name: str
    category: str
    type: str  # 'image' or 'kwgt'

class KLWPResponse(BaseModel):
    name: str
    type: str  # Either 'klwp' or 'image'

# Cache storage for different asset types
metadata_caches = {
    "wallpapers": {},
    "widgets": {},
    "klwp": {}
}

def load_cache(asset_type: str):
    """Load metadata cache from file for specific asset type."""
    cache_file = CACHE_FILES[asset_type]
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    return {}

def save_cache(asset_type: str, cache: Dict):
    """Save metadata cache to file for specific asset type."""
    cache_file = CACHE_FILES[asset_type]
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w") as f:
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

def update_wallpaper_cache():
    """Update the metadata cache for wallpapers."""
    assets = {}
    base_folder = ASSET_PATHS["wallpapers"]["base"]

    for subfolder in ASSET_PATHS["wallpapers"]["subfolders"]:
        folder = os.path.join(base_folder, subfolder)
        if not os.path.exists(folder):
            continue

        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(ASSET_PATHS["wallpapers"]["file_types"]):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder)
                    category = os.path.dirname(relative_path)
                    last_modified = os.path.getmtime(file_path)

                    cache_key = f"{subfolder}/{relative_path}"

                    if (cache_key in metadata_caches["wallpapers"] and 
                        metadata_caches["wallpapers"][cache_key]["last_modified"] == last_modified):
                        assets[cache_key] = metadata_caches["wallpapers"][cache_key]
                        continue

                    try:
                        size = os.path.getsize(file_path)
                        with Image.open(file_path) as img:
                            resolution = f"{img.width}x{img.height}"
                            colors = get_prominent_colors(file_path)
                    except Exception:
                        resolution = "Unknown"
                        colors = ["#000000"]

                    assets[cache_key] = {
                        "name": file,
                        "category": category if category else "root",
                        "resolution": resolution,
                        "size": size,
                        "colors": colors,
                        "last_modified": last_modified,
                        "folder_type": subfolder
                    }

    metadata_caches["wallpapers"] = assets
    save_cache("wallpapers", assets)

def update_widget_cache():
    """Update the metadata cache for widgets."""
    assets = {}
    base_folder = ASSET_PATHS["widgets"]["base"]

    if not os.path.exists(base_folder):
        return

    last_modified = {}
    for root, dirs, files in os.walk(base_folder):
        last_modified[root] = max(
            [os.path.getmtime(os.path.join(root, f)) for f in files]
            if files else [0]
        )

    if "last_modified" in metadata_caches["widgets"]:
        cache_is_valid = True
        for path, mtime in last_modified.items():
            if path not in metadata_caches["widgets"]["last_modified"] or \
               metadata_caches["widgets"]["last_modified"][path] != mtime:
                cache_is_valid = False
                break
                
        if cache_is_valid:
            return

    widgets_list = []
    for root, _, files in os.walk(base_folder):
        category = os.path.relpath(root, base_folder)
        if category == ".":
            continue

        for file in files:
            if file.endswith(ASSET_PATHS["widgets"]["file_types"]):
                file_type = 'kwgt' if file.endswith('.kwgt') else 'image'
                widgets_list.append({
                    "name": file,
                    "category": category,
                    "type": file_type
                })

    assets = {
        "widgets": widgets_list,
        "last_modified": last_modified
    }

    metadata_caches["widgets"] = assets
    save_cache("widgets", assets)

def update_klwp_cache():
    """Update the metadata cache for KLWP files."""
    assets = []
    base_folder = ASSET_PATHS["klwp"]["base"]

    if not os.path.exists(base_folder):
        return

    last_modified = os.path.getmtime(base_folder)

    # Check if the cache is up to date
    if "last_modified" in metadata_caches["klwp"] and \
       metadata_caches["klwp"]["last_modified"] == last_modified:
        return

    # Get all files with supported file types
    for file in os.listdir(base_folder):
        if file.endswith(ASSET_PATHS["klwp"]["file_types"]):
            file_type = 'klwp' if file.endswith('.klwp') else 'image'
            assets.append({
                "name": file,
                "type": file_type
            })

    assets = {
        "klwp": assets,
        "last_modified": last_modified
    }

    metadata_caches["klwp"] = assets
    save_cache("klwp", assets)


@app.on_event("startup")
def on_startup():
    """Load caches and update them on startup."""
    metadata_caches["wallpapers"] = load_cache("wallpapers")
    metadata_caches["widgets"] = load_cache("widgets")
    metadata_caches["klwp"] = load_cache("klwp")
    update_wallpaper_cache()
    update_widget_cache()
    update_klwp_cache()

@app.get("/wallpapers/{folder_type}", response_model=List[WallpaperResponse])
def list_wallpapers_by_folder(folder_type: str):
    """List wallpapers filtered by folder type."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    update_wallpaper_cache()
    filtered_assets = [
        data for data in metadata_caches["wallpapers"].values()
        if data["folder_type"] == folder_type
    ]

    if not filtered_assets:
        raise HTTPException(
            status_code=404,
            detail=f"No wallpapers found in folder '{folder_type}'."
        )
    return filtered_assets

@app.get("/widgets", response_model=List[WidgetResponse])
def list_all_widgets():
    """List all widgets with their types and categories."""
    update_widget_cache()
    return metadata_caches["widgets"]["widgets"]

@app.get("/klwp", response_model=List[KLWPResponse])
def list_all_klwp():
    """List all KLWP files and supported images."""
    update_klwp_cache()
    return metadata_caches["klwp"]["klwp"]


@app.get("/widgets/{category}", response_model=List[WidgetResponse])
def list_widgets_by_category(category: str):
    """List widgets in a specific category."""
    update_widget_cache()
    filtered_assets = [
        widget for widget in metadata_caches["widgets"]["widgets"]
        if widget["category"] == category
    ]

    if not filtered_assets:
        raise HTTPException(
            status_code=404,
            detail=f"No widgets found in category '{category}'."
        )
    return filtered_assets

@app.get("/widgets/{category}/{filename}")
def get_widget_file(category: str, filename: str):
    """
    Serve the actual widget file.
    """
    base_path = ASSET_PATHS["widgets"]["base"]
    file_path = os.path.join(base_path, category, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    if filename.endswith('.kwgt'):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    return FileResponse(path=file_path)

@app.get("/klwp/{filename}")  # Simplified KLWP file serving endpoint
def get_klwp_file(filename: str):
    """Serve the actual KLWP file"""
    base_path = ASSET_PATHS["klwp"]["base"]
    file_path = os.path.join(base_path, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    if filename.endswith('.klwp'):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    return FileResponse(path=file_path)

@app.get("/wallpapers/{folder_type}/{category}/{filename}")
def get_wallpaper_file(folder_type: str, category: str, filename: str):
    """Serve the actual wallpaper file."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    base_path = ASSET_PATHS["wallpapers"]["base"]
    file_path = os.path.join(base_path, folder_type, category, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
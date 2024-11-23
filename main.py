from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict, Literal, Union
import os
from PIL import Image
from collections import Counter
from pydantic import BaseModel
import json
import uvicorn
import aiofiles
import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor

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

# Pydantic models remain the same
class WallpaperResponse(BaseModel):
    name: str
    category: str
    resolution: str
    size: int
    colors: List[str]

class WidgetResponse(BaseModel):
    name: str
    category: str
    type: str

class KLWPResponse(BaseModel):
    name: str
    type: str

# Cache storage
metadata_caches = {
    "wallpapers": {},
    "widgets": {},
    "klwp": {}
}

# Create a ThreadPoolExecutor for CPU-bound tasks
thread_pool = ThreadPoolExecutor()

async def load_cache(asset_type: str) -> Dict:
    """Async load metadata cache from file."""
    cache_file = CACHE_FILES[asset_type]
    if os.path.exists(cache_file):
        async with aiofiles.open(cache_file, "r") as f:
            content = await f.read()
            return json.loads(content)
    return {}

async def save_cache(asset_type: str, cache: Dict):
    """Async save metadata cache to file."""
    cache_file = CACHE_FILES[asset_type]
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    async with aiofiles.open(cache_file, "w") as f:
        await f.write(json.dumps(cache, indent=4))

def get_prominent_colors(image_path: str, num_colors: int = 5) -> List[str]:
    """Extract prominent colors from an image (CPU-bound, runs in thread pool)."""
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

async def process_wallpaper(file_path: str, subfolder: str, relative_path: str, last_modified: float):
    """Process a single wallpaper file asynchronously."""
    category = os.path.dirname(relative_path)
    cache_key = f"{subfolder}/{relative_path}"
    size = os.path.getsize(file_path)

    # Run CPU-bound image processing in thread pool
    loop = asyncio.get_running_loop()
    colors = await loop.run_in_executor(thread_pool, get_prominent_colors, file_path)
    
    resolution = "Unknown"
    try:
        with Image.open(file_path) as img:
            resolution = f"{img.width}x{img.height}"
    except Exception:
        pass

    return cache_key, {
        "name": os.path.basename(file_path),
        "category": category if category else "root",
        "resolution": resolution,
        "size": size,
        "colors": colors,
        "last_modified": last_modified,
        "folder_type": subfolder
    }

async def update_wallpaper_cache():
    """Async update the metadata cache for wallpapers."""
    assets = {}
    base_folder = ASSET_PATHS["wallpapers"]["base"]
    tasks = []

    for subfolder in ASSET_PATHS["wallpapers"]["subfolders"]:
        folder = os.path.join(base_folder, subfolder)
        if not os.path.exists(folder):
            continue

        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(ASSET_PATHS["wallpapers"]["file_types"]):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder)
                    last_modified = os.path.getmtime(file_path)

                    cache_key = f"{subfolder}/{relative_path}"
                    if (cache_key in metadata_caches["wallpapers"] and 
                        metadata_caches["wallpapers"][cache_key]["last_modified"] == last_modified):
                        assets[cache_key] = metadata_caches["wallpapers"][cache_key]
                        continue

                    tasks.append(process_wallpaper(file_path, subfolder, relative_path, last_modified))

    if tasks:
        results = await asyncio.gather(*tasks)
        for cache_key, data in results:
            assets[cache_key] = data

    metadata_caches["wallpapers"] = assets
    await save_cache("wallpapers", assets)

async def update_widget_cache():
    """Async update the metadata cache for widgets."""
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
    await save_cache("widgets", assets)

async def update_klwp_cache():
    """Async update the metadata cache for KLWP files."""
    assets = []
    base_folder = ASSET_PATHS["klwp"]["base"]

    if not os.path.exists(base_folder):
        return

    last_modified = os.path.getmtime(base_folder)

    if "last_modified" in metadata_caches["klwp"] and \
       metadata_caches["klwp"]["last_modified"] == last_modified:
        return

    for file in os.listdir(base_folder):
        if file.endswith(ASSET_PATHS["klwp"]["file_types"]):
            file_type = 'klwp' if file.endswith('.klwp') else 'image'
            assets.append({
                "name": file,
                "type": file_type
            })

    assets_dict = {
        "klwp": assets,
        "last_modified": last_modified
    }

    metadata_caches["klwp"] = assets_dict
    await save_cache("klwp", assets_dict)

@app.on_event("startup")
async def on_startup():
    """Async load caches and update them on startup."""
    metadata_caches["wallpapers"] = await load_cache("wallpapers")
    metadata_caches["widgets"] = await load_cache("widgets")
    metadata_caches["klwp"] = await load_cache("klwp")
    await asyncio.gather(
        update_wallpaper_cache(),
        update_widget_cache(),
        update_klwp_cache()
    )

@app.get("/wallpapers/{folder_type}", response_model=List[WallpaperResponse])
async def list_wallpapers_by_folder(folder_type: str):
    """List wallpapers filtered by folder type."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    await update_wallpaper_cache()
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
async def list_all_widgets():
    """List all widgets with their types and categories."""
    await update_widget_cache()
    return metadata_caches["widgets"]["widgets"]

@app.get("/klwp", response_model=List[KLWPResponse])
async def list_all_klwp():
    """List all KLWP files and supported images."""
    await update_klwp_cache()
    return metadata_caches["klwp"]["klwp"]

@app.get("/widgets/{category}", response_model=List[WidgetResponse])
async def list_widgets_by_category(category: str):
    """List widgets in a specific category."""
    await update_widget_cache()
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
async def get_widget_file(category: str, filename: str):
    """Serve the actual widget file."""
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

@app.get("/klwp/{filename}")
async def get_klwp_file(filename: str):
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
async def get_wallpaper_file(folder_type: str, category: str, filename: str):
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

@app.get("/wallpapers/{folder_type}/{category}", response_model=List[WallpaperResponse])
async def list_wallpapers_by_category(folder_type: str, category: str):
    """List all wallpapers in a specific category folder."""
    if folder_type not in {"hq", "mid"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder type. Use 'hq' or 'mid'."
        )

    await update_wallpaper_cache()
    
    # Filter assets by both folder type and category
    filtered_assets = [
        data for data in metadata_caches["wallpapers"].values()
        if data["folder_type"] == folder_type and data["category"] == category
    ]

    if not filtered_assets:
        raise HTTPException(
            status_code=404,
            detail=f"No wallpapers found in category '{category}' for folder type '{folder_type}'."
        )
    
    # Sort by name for consistent ordering
    return sorted(filtered_assets, key=lambda x: x["name"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
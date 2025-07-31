import traceback
from typing import List, Dict
import os
from PIL import Image
import json
import uvicorn
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sklearn.cluster import KMeans
import numpy as np

from config import ASSET_PATHS, CACHE_FILES

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
    """
    Extract prominent colors using a faster k-means configuration,
    and handle images with few colors gracefully.
    """
    try:
        with Image.open(image_path) as img:
            img = img.resize((100, 100))
            img = img.convert("RGB")
            pixels = np.array(img).reshape(-1, 3)

        unique_pixels = np.unique(pixels, axis=0)

        if len(unique_pixels) < num_colors:
            colors = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in unique_pixels]
            padding_color = colors[0] if colors else "#000000"
            while len(colors) < num_colors:
                colors.append(padding_color)
            return colors[:num_colors]

        # --- OPTIMIZATION ---
        # Changed n_init from 10 to 1 for a major speed improvement.
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=1) 
        kmeans.fit(pixels)
        cluster_centers = kmeans.cluster_centers_

        colors = [f"#{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in cluster_centers]
        return colors
        
    except Exception as e:
        # Improved error logging to show the exact problem
        print(f"--- DETAILED ERROR in get_prominent_colors ---")
        print(f"File: {image_path}")
        print(traceback.format_exc())
        print(f"--------------------------------------------")
        return ["#000000"] * num_colors

async def process_wallpaper(file_path: str, subfolder: str, relative_path: str, last_modified: float):
    """Process a single wallpaper file asynchronously."""
    category = os.path.dirname(relative_path)
    cache_key = f"{subfolder}/{relative_path}"
    size = os.path.getsize(file_path)

    # Run CPU-bound image processing in thread pool with a timeout
    loop = asyncio.get_running_loop()
    try:
        colors = await asyncio.wait_for(
            loop.run_in_executor(thread_pool, get_prominent_colors, file_path),
            timeout=10.0  # 10-second timeout for color extraction
        )
    except asyncio.TimeoutError:
        print(f"Timeout processing image for prominent colors: {file_path}")
        colors = ["#000000"] * 5  # Default colors on timeout
    
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

    for subfolder in ASSET_PATHS["wallpapers"]["subfolders"]:  # Includes 'low'
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

    widgets_list = []
    for root, _, files in os.walk(base_folder):
        category = os.path.relpath(root, base_folder)
        for file in files:
            if file.endswith(ASSET_PATHS["widgets"]["file_types"]):
                file_path = os.path.join(root, file)
                file_type = 'kwgt' if file.endswith('.kwgt') else 'image'
                last_modified = os.path.getmtime(file_path)

                widgets_list.append({
                    "name": file,
                    "category": category if category != "." else "root",
                    "type": file_type,
                    "last_modified": last_modified
                })

    assets = {
        "widgets": widgets_list
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

    if "last_modified" in metadata_caches["klwp"] and metadata_caches["klwp"]["last_modified"] == last_modified:
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

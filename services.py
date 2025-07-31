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
    """Extract the most prominent colors from an image using k-means clustering."""
    try:
        # Open and process the image
        with Image.open(image_path) as img:
            # Convert to RGB first to handle various formats (RGBA, P, L, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize for faster processing but keep reasonable quality
            # Use thumbnail to maintain aspect ratio
            img.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            pixels = np.array(img)
            
            # Check if image is valid
            if pixels.size == 0:
                print(f"Empty image: {image_path}")
                return ["#808080"] * num_colors  # Return gray instead of black
            
            # Reshape to list of RGB pixels
            pixels = pixels.reshape(-1, 3)
            
            # Remove any invalid pixels (just in case)
            pixels = pixels[~np.isnan(pixels).any(axis=1)]
            
            if len(pixels) == 0:
                print(f"No valid pixels found: {image_path}")
                return ["#808080"] * num_colors
            
            # Ensure we don't have more clusters than pixels
            actual_num_colors = min(num_colors, len(np.unique(pixels, axis=0)))
            if actual_num_colors < num_colors:
                print(f"Image has fewer unique colors than requested: {image_path}")
            
            # Apply k-means clustering
            kmeans = KMeans(
                n_clusters=actual_num_colors, 
                random_state=42, 
                n_init=10,
                max_iter=100  # Limit iterations to prevent hanging
            )
            
            kmeans.fit(pixels.astype(np.float64))  # Ensure float64 for better precision
            cluster_centers = kmeans.cluster_centers_
            
            # Get cluster labels and counts to sort by popularity
            labels = kmeans.labels_
            label_counts = np.bincount(labels)
            
            # Sort colors by popularity (most frequent first)
            sorted_indices = np.argsort(-label_counts)
            sorted_centers = cluster_centers[sorted_indices]
            
            # Convert RGB values to hex colors with proper bounds checking
            colors = []
            for center in sorted_centers:
                r, g, b = center
                # Ensure values are within valid range [0, 255]
                r = max(0, min(255, int(round(r))))
                g = max(0, min(255, int(round(g))))
                b = max(0, min(255, int(round(b))))
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                colors.append(hex_color)
            
            # Pad with gray if we have fewer colors than requested
            while len(colors) < num_colors:
                colors.append("#808080")
            
            return colors[:num_colors]
            
    except Exception as e:
        print(f"Error processing image {image_path}: {type(e).__name__}: {e}")
        # Return gray colors instead of black to distinguish from actual black images
        return ["#808080"] * num_colors

async def process_wallpaper(file_path: str, subfolder: str, relative_path: str, last_modified: float):
    """Process a single wallpaper file asynchronously."""
    category = os.path.dirname(relative_path)
    cache_key = f"{subfolder}/{relative_path}"
    size = os.path.getsize(file_path)

    # Check if file is accessible and not corrupted
    try:
        # Quick file validation
        with open(file_path, 'rb') as f:
            # Read first few bytes to ensure file is accessible
            header = f.read(100)
            if len(header) < 10:
                print(f"File too small or corrupted: {file_path}")
                colors = ["#ff0000"]  # Red to indicate error
            else:
                # Run CPU-bound image processing in thread pool with extended timeout
                loop = asyncio.get_running_loop()
                try:
                    colors = await asyncio.wait_for(
                        loop.run_in_executor(thread_pool, get_prominent_colors, file_path),
                        timeout=30.0  # Increased timeout to 30 seconds
                    )
                except asyncio.TimeoutError:
                    print(f"Timeout processing image for prominent colors: {file_path}")
                    colors = ["#ffa500"] * 5  # Orange to indicate timeout
                except Exception as e:
                    print(f"Error in thread pool execution for {file_path}: {e}")
                    colors = ["#ff0000"] * 5  # Red to indicate error
    except Exception as e:
        print(f"File access error for {file_path}: {e}")
        colors = ["#ff0000"] * 5  # Red to indicate file access error
    
    # Get resolution with better error handling
    resolution = "Unknown"
    try:
        with Image.open(file_path) as img:
            resolution = f"{img.width}x{img.height}"
    except Exception as e:
        print(f"Could not get resolution for {file_path}: {e}")

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
                    
                    # Skip files that are too small (likely corrupted)
                    try:
                        if os.path.getsize(file_path) < 1024:  # Less than 1KB
                            print(f"Skipping very small file: {file_path}")
                            continue
                    except OSError:
                        print(f"Cannot access file: {file_path}")
                        continue
                    
                    relative_path = os.path.relpath(file_path, folder)
                    last_modified = os.path.getmtime(file_path)

                    cache_key = f"{subfolder}/{relative_path}"
                    if (cache_key in metadata_caches["wallpapers"] and 
                        metadata_caches["wallpapers"][cache_key]["last_modified"] == last_modified):
                        assets[cache_key] = metadata_caches["wallpapers"][cache_key]
                        continue

                    tasks.append(process_wallpaper(file_path, subfolder, relative_path, last_modified))

    if tasks:
        # Process tasks in smaller batches to prevent overwhelming the system
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"Task failed with exception: {result}")
                else:
                    cache_key, data = result
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
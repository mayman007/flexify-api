from fastapi import FastAPI, HTTPException
from typing import List, Dict
import os
from PIL import Image
from collections import Counter
from fastapi.responses import FileResponse
from pydantic import BaseModel

import uvicorn

app = FastAPI()

# Path to the folder where wallpapers are stored
WALLPAPERS_FOLDER = "../flexify_assets/wallpapers"


# Define a Pydantic model for the response
class WallpaperResponse(BaseModel):
    name: str
    category: str
    resolution: str
    size: int
    colors: List[str]


def get_prominent_colors(image_path: str, num_colors: int = 5) -> List[str]:
    """Extract prominent colors from an image."""
    try:
        with Image.open(image_path) as img:
            # Resize the image to speed up color analysis
            img = img.resize((100, 100))
            # Convert image to RGB mode
            img = img.convert("RGB")
            # Get a list of all pixels in the image
            pixels = list(img.getdata())
            # Count the most common colors
            color_counts = Counter(pixels).most_common(num_colors)
            # Convert RGB tuples to hex color codes
            colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in color_counts]
            return colors
    except Exception:
        return ["#000000"]  # Return black as a fallback in case of an error


@app.get("/wallpapers", response_model=List[WallpaperResponse])
def list_wallpapers():
    """List all wallpaper files with their metadata."""
    try:
        wallpapers = []
        
        for root, _, files in os.walk(WALLPAPERS_FOLDER):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    file_path = os.path.join(root, file)
                    category = os.path.relpath(root, WALLPAPERS_FOLDER)
                    size = os.path.getsize(file_path)
                    
                    try:
                        with Image.open(file_path) as img:
                            resolution = f"{img.width}x{img.height}"
                            colors = get_prominent_colors(file_path)
                    except Exception:
                        resolution = "Unknown"
                        colors = ["#000000"]
                    
                    wallpapers.append({
                        "name": file,
                        "category": category,
                        "resolution": resolution,
                        "size": size,
                        "colors": colors
                    })

        if not wallpapers:
            raise HTTPException(status_code=404, detail="No wallpapers found in wallpapers folder or subfolders.")
        
        return wallpapers
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Wallpapers folder not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wallpapers/{wallpaper_name:path}")
def get_wallpaper(wallpaper_name: str):
    """Serve a wallpaper file from the wallpapers directory or its subdirectories."""
    requested_path = os.path.normpath(os.path.join(WALLPAPERS_FOLDER, wallpaper_name))
    if not requested_path.startswith(os.path.abspath(WALLPAPERS_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path.")
    
    if not os.path.isfile(requested_path):
        raise HTTPException(status_code=404, detail="Wallpaper not found.")
    
    return FileResponse(requested_path)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

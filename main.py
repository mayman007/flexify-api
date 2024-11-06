from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

import uvicorn

app = FastAPI()

# origins = ['http://localhost:3000','http://192.168.178.23:3000', "http://192.168.0.116:8000"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# Path to the folder where images are stored
WALLPAPERS_FOLDER = "flexify_assets/wallpapers"


@app.get("/images", response_model=List[str])
def list_images():
    """List all image filenames in the wallpapers directory."""
    try:
        # List all files in the directory
        files = os.listdir(WALLPAPERS_FOLDER)
        # Filter for image files by extension
        image_files = [file for file in files if file.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not image_files:
            raise HTTPException(status_code=404, detail="No images found in wallpapers folder.")
        
        return image_files
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Wallpapers folder not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/images/{image_name}")
def get_image(image_name: str):
    """Serve an image file from the wallpapers directory."""
    image_path = os.path.join(WALLPAPERS_FOLDER, image_name)
    
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Image not found.")
    
    return FileResponse(image_path)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List
import os

import services
from models import WallpaperResponse, WidgetResponse, KLWPResponse
from config import ASSET_PATHS

router = APIRouter()

@router.get("/wallpapers/{folder_type}", response_model=List[WallpaperResponse])
async def list_wallpapers_by_folder(folder_type: str):
    """List wallpapers filtered by folder type and sorted by last_modified."""
    await services.update_wallpaper_cache()
    filtered_assets = [
        data for data in services.metadata_caches["wallpapers"].values()
        if data["folder_type"] == folder_type
    ]
    return sorted(filtered_assets, key=lambda x: x["last_modified"], reverse=True)

@router.get("/widgets", response_model=List[WidgetResponse])
async def list_all_widgets():
    """List all widgets with their types and categories, sorted by last_modified."""
    await services.update_widget_cache()
    widgets = services.metadata_caches["widgets"]["widgets"]
    return sorted(widgets, key=lambda x: x.get("last_modified", 0), reverse=True)


@router.get("/klwp", response_model=List[KLWPResponse])
async def list_all_klwp():
    """List all KLWP files and supported images, sorted by last_modified."""
    await services.update_klwp_cache()
    klwp = services.metadata_caches["klwp"]["klwp"]
    return sorted(klwp, key=lambda x: x.get("last_modified", 0), reverse=True)


@router.get("/widgets/{category}", response_model=List[WidgetResponse])
async def list_widgets_by_category(category: str):
    """List widgets in a specific category, sorted by last_modified."""
    await services.update_widget_cache()
    filtered_assets = [
        widget for widget in services.metadata_caches["widgets"]["widgets"]
        if widget["category"] == category
    ]
    return sorted(filtered_assets, key=lambda x: x.get("last_modified", 0), reverse=True)


@router.get("/wallpapers/{folder_type}/{category}", response_model=List[WallpaperResponse])
async def list_wallpapers_by_category(folder_type: str, category: str):
    """List all wallpapers in a specific category folder, sorted by last_modified."""
    await services.update_wallpaper_cache()
    filtered_assets = [
        data for data in services.metadata_caches["wallpapers"].values()
        if data["folder_type"] == folder_type and data["category"] == category
    ]
    return sorted(filtered_assets, key=lambda x: x["last_modified"], reverse=True)



@router.get("/widgets/{category}/{filename}")
async def get_widget_file(category: str, filename: str):
    """Serve the actual widget file."""
    base_path = ASSET_PATHS["widgets"]["base"]

    # If category is 'root', it refers to the base of the widgets directory
    path_parts = [base_path]
    if category != "root":
        path_parts.append(category)
    path_parts.append(filename)
    file_path = os.path.join(*path_parts)

    # Security check for path traversal
    abs_base_path = os.path.abspath(base_path)
    abs_file_path = os.path.abspath(file_path)
    if not abs_file_path.startswith(abs_base_path):
        raise HTTPException(status_code=403, detail="Access forbidden.")

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

@router.get("/klwp/{filename}")
async def get_klwp_file(filename: str):
    """Serve the actual KLWP file"""
    base_path = ASSET_PATHS["klwp"]["base"]
    file_path = os.path.join(base_path, filename)

    abs_base_path = os.path.abspath(base_path)
    abs_file_path = os.path.abspath(file_path)
    if not abs_file_path.startswith(abs_base_path):
        raise HTTPException(status_code=403, detail="Access forbidden.")

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

@router.get("/wallpapers/{folder_type}/{category}/{filename}")
async def get_wallpaper_file(folder_type: str, category: str, filename: str):
    """Serve the actual wallpaper file with fallback from .png to .jpg"""
    base_path = ASSET_PATHS["wallpapers"]["base"]

    # Security: Ensure folder_type is one of the allowed subfolders
    if folder_type not in ASSET_PATHS["wallpapers"]["subfolders"]:
        raise HTTPException(status_code=404, detail="Folder type not found.")

    # If category is 'root', it refers to the base of the folder_type directory
    path_parts = [base_path, folder_type]
    if category != "root":
        path_parts.append(category)

    file_path = os.path.join(*path_parts, filename)

    # Security check for path traversal
    abs_base_path = os.path.abspath(base_path)
    abs_file_path = os.path.abspath(file_path)
    if not abs_file_path.startswith(abs_base_path):
        raise HTTPException(status_code=403, detail="Access forbidden.")

    # First try the requested file
    if os.path.exists(file_path):
        return FileResponse(file_path)

    # If requested file is PNG and doesn't exist, try JPG
    root, ext = os.path.splitext(filename)
    if ext.lower() == '.png':
        jpg_filename = root + '.jpg'
        jpg_path = os.path.join(*path_parts, jpg_filename)
        if os.path.exists(jpg_path):
            return FileResponse(jpg_path)

    # If neither exists, show error
    raise HTTPException(
        status_code=404,
        detail=f"nothin"
    )

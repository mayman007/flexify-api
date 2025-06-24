from pydantic import BaseModel
from typing import List

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

from fastapi import FastAPI
import uvicorn
import asyncio
from contextlib import asynccontextmanager

import services
from routers import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown."""
    # Startup logic
    services.metadata_caches["wallpapers"] = await services.load_cache("wallpapers")
    services.metadata_caches["widgets"] = await services.load_cache("widgets")
    services.metadata_caches["klwp"] = await services.load_cache("klwp")
    await asyncio.gather(
        services.update_wallpaper_cache(),
        services.update_widget_cache(),
        services.update_klwp_cache()
    )
    yield  # Application runs here
    # Shutdown logic (if any) can go here

app = FastAPI(lifespan=lifespan)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
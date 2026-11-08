import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from core.database import db
from core.scheduler import proactive_scheduler
from api.whatsapp_routes import whatsapp_router
from api.admin_routes import admin_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("aura")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "images" / "generated").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    db.init_database()
    proactive_scheduler.start()
    
    # Ensure default avatar reference image exists
    ref_img = STATIC_DIR / "images" / "aura_canonical_reference.jpg"
    if not ref_img.exists():
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (768, 1024), color=(40, 20, 35))
            draw = ImageDraw.Draw(img)
            draw.text((220, 500), "Aura Character Reference", fill=(245, 180, 200))
            img.save(str(ref_img), "JPEG")
        except Exception as e:
            logger.warning("Could not create initial placeholder image: %s", e)

    yield
    # Shutdown tasks
    logger.info("Shutting down %s...", settings.APP_NAME)
    proactive_scheduler.shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Intelligent, realistic AI Girlfriend WhatsApp Bot using free & open-source technologies.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount API Routers
app.include_router(whatsapp_router, prefix="/api/whatsapp")
app.include_router(whatsapp_router, prefix="")  # Allows /webhook directly for Meta compatibility
app.include_router(admin_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Project AURA Server is Running</h1><p>Visit /docs for API schema</p>")

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
        "primary_ai": settings.PRIMARY_AI_PROVIDER
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

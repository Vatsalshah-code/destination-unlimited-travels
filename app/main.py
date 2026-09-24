import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import BASE_DIR
from app.database import init_db
from app.routes.public_routes import router as public_router
from app.routes.admin_routes import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is initialized and seeded
    init_db()
    print("[SYSTEM] Visa & Passport Document Management System initialized.")
    yield
    # Shutdown
    print("[SYSTEM] Visa & Passport Document Management System stopped.")

app = FastAPI(
    title="Visa & Passport Client Document Management System",
    description="Secure public client intake form and private administrative document management portal.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for secure integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets (CSS, JS, icons)
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routes
app.include_router(public_router)
app.include_router(admin_router)

# Custom 404 and 500 error handlers
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"success": False, "detail": "Resource not found."})
    return JSONResponse(status_code=404, content={"message": "Page not found."})

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"success": False, "detail": "Internal server error occurred."})

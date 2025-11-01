"""
Главное FastAPI приложение банка
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from config import config
from database import engine
from models import Base
from api import (
    accounts, auth, consents, payments, admin, products, well_known, 
    banker, product_agreements,
    product_applications, customer_leads, product_offers, product_offer_consents,
    vrp_consents, vrp_payments
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    print(f"🏦 Starting {config.BANK_NAME} ({config.BANK_CODE})")
    print(f"📍 Database: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else 'local'}")
    
    # Create tables (в production использовать Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    print(f"🛑 Stopping {config.BANK_NAME}")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=f"{config.BANK_NAME} API",
    description=f"OpenBanking Russia v{config.API_VERSION} compatible API",
    version=config.API_VERSION,
    lifespan=lifespan
)

# CORS - разрешить запросы между всеми банками
# Для мультибанковых приложений нужно разрешить cross-origin запросы
allowed_origins = [
    "https://onebank.ru",
    "https://hackapi.tech",
    "http://localhost",
    "http://localhost:*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Все банки + прокси
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(consents.router)
app.include_router(payments.router)
app.include_router(products.router)
app.include_router(product_agreements.router)
app.include_router(product_applications.router)
app.include_router(customer_leads.router)
app.include_router(product_offers.router)
app.include_router(product_offer_consents.router)
app.include_router(vrp_consents.router)
app.include_router(vrp_payments.router)
app.include_router(banker.router)
app.include_router(admin.router)
app.include_router(well_known.router)

# Mount static files (frontend)
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/client", StaticFiles(directory=str(frontend_path / "client"), html=True), name="client")
    app.mount("/banker", StaticFiles(directory=str(frontend_path / "banker"), html=True), name="banker")

# Mount admin panel (from root)
# Try both relative and absolute paths
admin_panel_path = Path(__file__).parent.parent / "admin-panel"
if not admin_panel_path.exists():
    # Fallback to absolute path in Docker
    admin_panel_path = Path("/app/admin-panel")

if admin_panel_path.exists():
    print(f"Mounting admin panel from: {admin_panel_path}")
    app.mount("/admin", StaticFiles(directory=str(admin_panel_path), html=True), name="admin")
else:
    print(f"Warning: admin-panel directory not found at {admin_panel_path}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "bank": config.BANK_NAME,
        "bank_code": config.BANK_CODE,
        "api_version": config.API_VERSION,
        "status": "online"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "bank": config.BANK_CODE,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    # Определяем порт на основе bank_code
    port_map = {
        "vbank": 8001,
        "abank": 8002,
        "sbank": 8003
    }
    port = port_map.get(config.BANK_CODE, 8001)
    
    uvicorn.run(app, host="0.0.0.0", port=port)


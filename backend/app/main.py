"""Point d'entrée FastAPI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import sys

from .config import settings
from .database import engine, Base, AsyncSessionLocal
from .api import auth, users, vault, demarches, cerfas, ai, tts, gouv, admin
from .core.bootstrap import bootstrap_admin


# Logger
logger.remove()
logger.add(sys.stdout, level=settings.LOG_LEVEL, serialize=settings.APP_ENV == "production")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown."""
    logger.info(f"🚀 {settings.APP_NAME} starting · env={settings.APP_ENV}")
    # Auto-create tables (en prod, utiliser Alembic à la place)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Bootstrap admin
    async with AsyncSessionLocal() as db:
        await bootstrap_admin(db)
    logger.info("✅ Backend prêt")
    yield
    logger.info("👋 Backend arrêté")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Plateforme de simplification administrative française assistée par IA.",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.APP_ENV == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} → {response.status_code}")
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Erreur non gérée : {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erreur interne"})


# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Utilisateurs"])
app.include_router(vault.router, prefix="/api/vault", tags=["Coffre-fort"])
app.include_router(demarches.router, prefix="/api/demarches", tags=["Démarches"])
app.include_router(cerfas.router, prefix="/api/cerfas", tags=["CERFAs"])
app.include_router(ai.router, prefix="/api/ai", tags=["IA juridique"])
app.include_router(tts.router, prefix="/api/tts", tags=["Synthèse vocale"])
app.include_router(gouv.router, prefix="/api/gouv", tags=["APIs Gouv.fr"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs" if settings.DEBUG else "disabled in prod",
    }

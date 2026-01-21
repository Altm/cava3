import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.common.logging import setup_logging
from app.api.v1.routes import auth, products, sales, catalog, users, stock
from app.audit.middleware import RequestLoggingMiddleware
from app.audit.listeners import register_listeners
from app.infrastructure.db.session import SessionLocal
from app.security.auth import get_password_hash
from app.models.models import User


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, settings.structlog_json)
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if settings.swagger_enabled else None,
        redoc_url="/redoc" if settings.swagger_enabled else None,
        openapi_url="/openapi.json" if settings.swagger_enabled else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(sales.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(stock.router, prefix="/api/v1")

    register_listeners()

    @app.on_event("startup")
    def ensure_default_admin():
        """Bootstrap admin user if missing."""
        with SessionLocal() as session:
            user = session.query(User).filter(User.username == settings.admin_username).first()
            if not user:
                admin = User(
                    username=settings.admin_username,
                    password_hash=get_password_hash(settings.admin_password),
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin)
                session.commit()

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

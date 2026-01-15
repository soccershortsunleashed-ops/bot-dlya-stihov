from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.infra.config.logging import setup_logging
from app.web.routes import yookassa_webhook, admin
import logging

def create_app() -> FastAPI:
    setup_logging()
    logger = logging.getLogger(__name__)
    
    app = FastAPI(
        title="Creative Funnel Bot Platform API",
        description="Admin panel and webhooks for the bot platform",
        version="0.1.0"
    )

    # Static files
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

    # Routers
    app.include_router(yookassa_webhook.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    @app.get("/")
    async def root():
        # Перенаправление на административную панель
        logger.info("Root path accessed, redirecting to admin dashboard")
        redirect_url = "/admin/dashboard"
        logger.info(f"Redirect URL: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app

app = create_app()
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.services.i18n_db import DBI18n
from app.services.menu import get_menu_tree
from app.config import settings
from app.db import SessionLocal
from app.ui import get_footer_data


class ContextInjectorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Buka sesi DB baru
        db = SessionLocal()
        try:
            # Dapatkan bahasa aktif
            lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
            # Siapkan context umum
            request.state.lang = lang
            request.state.db = db
            request.state.i18n = DBI18n(db, lang)
            request.state.admin = request.session.get("admin")
            request.state.header_menu = get_menu_tree(
                db, lang, "header", admin_logged=bool(request.state.admin)
            )
            request.state.footer_data = get_footer_data(db, lang)

            # Lanjutkan request
            response = await call_next(request)
            return response
        finally:
            db.close()

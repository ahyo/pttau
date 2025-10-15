from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.services.i18n_db import DBI18n
from app.services.menu import get_menu_tree
from app.config import settings
from app.db import SessionLocal
from app.ui import get_footer_data


class ContextInjectorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        db = SessionLocal()
        try:
            lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
            request.state.lang = lang
            request.state.db = db

            # aman dari error
            try:
                request.state.i18n = DBI18n(db, lang)
            except Exception as e:
                print("⚠️ i18n init failed:", e)
                request.state.i18n = None

            admin = None
            if "session" in request.scope:
                admin = request.session.get("admin")
            request.state.admin = admin

            request.state.header_menu = get_menu_tree(
                db, lang, "header", admin_logged=bool(admin)
            )
            request.state.footer_data = get_footer_data(db, lang)

            response = await call_next(request)
            return response
        finally:
            db.close()

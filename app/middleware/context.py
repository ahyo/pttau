from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.services.i18n_db import DBI18n
from app.services.menu import get_menu_tree
from app.config import settings
from app.db import SessionLocal
from sqlalchemy import select, func

from app.ui import get_footer_data
from app.models.cart import Cart, CartItem


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
            user = None
            if "session" in request.scope:
                admin = request.session.get("admin")
                user = request.session.get("user")
            request.state.admin = admin
            request.state.user = user

            cart_count = 0
            if user:
                try:
                    cart_count = (
                        db.execute(
                            select(func.coalesce(func.sum(CartItem.quantity), 0))
                            .join(Cart, Cart.id == CartItem.cart_id)
                            .where(Cart.user_id == user["id"], Cart.status == "open")
                        ).scalar()
                        or 0
                    )
                except Exception:
                    cart_count = 0
            request.state.cart_count = cart_count

            request.state.header_menu = get_menu_tree(
                db, lang, "header", admin_logged=bool(admin)
            )
            request.state.footer_data = get_footer_data(db, lang)

            response = await call_next(request)
            return response
        finally:
            db.close()

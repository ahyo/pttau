from fastapi import FastAPI, Request, Response
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.db import get_db
from app.i18n import pick_lang
from app.routers import (
    admin_carousel,
    admin_footer,
    admin_menu,
    admin_product,
    auth,
    catalog,
    cart,
    product_page,
    site,
    api_public,
    admin,
)
import logging, os
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.i18n_db import DBI18n
from app.middleware.context import ContextInjectorMiddleware

# bahasa
VALID_LANGS = {"id", "en", "ar"}

os.makedirs("app/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app/logs/app.log", encoding="utf-8"),
        logging.StreamHandler(),  # agar juga muncul di Passenger log
    ],
)
logger = logging.getLogger("ptaero")


app = FastAPI(
    title=settings.APP_NAME,
    middleware=[
        Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY),
        Middleware(ContextInjectorMiddleware),
    ],
)


app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = settings


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # minimal context supaya navbar tetap punya i18n/lang
        db = next(get_db())
        lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
        i18n = DBI18n(db, lang)
        return templates.TemplateResponse(
            "site/404.html",
            {"request": request, "lang": lang, "i18n": i18n},
            status_code=404,
        )
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)


@app.middleware("http")
async def lang_middleware(request: Request, call_next):
    lang = pick_lang(request, default_lang=settings.DEFAULT_LANG)
    request.state.lang = lang
    response: Response = await call_next(request)
    # persist cookie selama 1 tahun
    if request.query_params.get("lang") in {"id", "en", "ar"}:
        response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


def set_lang_cookie(resp: Response, lang: str):
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")


@app.get("/health")
def health():
    logger.info("Health check hit")
    return {"ok": True}


@app.get("/set-lang/{code}")
async def set_lang(code: str, request: Request):
    lang = code if code in VALID_LANGS else settings.DEFAULT_LANG
    # redirect ke halaman sebelumnya (atau ke '/')
    back = request.headers.get("referer") or "/"
    resp = RedirectResponse(url=back, status_code=302)
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(product_page.router)
app.include_router(site.router)
app.include_router(api_public.router, prefix="/api")
app.include_router(admin.router, prefix="")
app.include_router(admin_carousel.router)
app.include_router(admin_footer.router)
app.include_router(admin_menu.router)
app.include_router(admin_product.router)

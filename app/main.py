from fastapi import FastAPI, Request, Response
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.db import get_db
from app.routers import (
    admin_carousel,
    admin_footer,
    admin_menu,
    admin_product,
    admin_order,
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

from app.middleware.context import ContextInjectorMiddleware

# s
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


def choose_lang(request: Request) -> str:
    query_lang = request.query_params.get("lang")
    if query_lang in VALID_LANGS:
        return query_lang
    cookie_lang = request.cookies.get("lang")
    if cookie_lang in VALID_LANGS:
        return cookie_lang
    return settings.DEFAULT_LANG


@app.middleware("http")
async def lang_middleware(request: Request, call_next):
    lang = choose_lang(request)
    request.state.lang = lang
    response: Response = await call_next(request)
    if request.query_params.get("lang") in VALID_LANGS:
        response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # minimal context supaya navbar tetap punya informasi dasar
        db = next(get_db())
        lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
        return templates.TemplateResponse(
            "site/404.html",
            {"request": request, "lang": lang},
            status_code=404,
        )
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)


@app.get("/health")
def health():
    logger.info("Health check hit")
    return {"ok": True}


@app.get("/set-lang/{code}")
async def set_lang(code: str, request: Request):
    lang = code if code in VALID_LANGS else settings.DEFAULT_LANG
    referer = request.headers.get("referer") or "/"
    response = Response(status_code=302)
    response.headers["Location"] = referer
    response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


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
app.include_router(admin_order.router)

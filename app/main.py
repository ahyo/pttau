from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.routers import site, api_public
import logging, os

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

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def set_lang_cookie(resp: Response, lang: str):
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")


@app.get("/health")
def health():
    logger.info("Health check hit")
    return {"ok": True}


@app.get("/set-lang/{code}")
async def set_lang(code: str):
    from .i18n import UI_STRINGS

    lang = code if code in UI_STRINGS else "id"
    resp = Response(status_code=302)
    set_lang_cookie(resp, lang)
    resp.headers["Location"] = "/"
    return resp


app.include_router(site.router)
app.include_router(api_public.router, prefix="/api")

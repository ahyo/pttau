from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.i18n_db import DBI18n
from app.db import get_db
from app.config import settings

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db=Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    news = []
    items = []
    return templates.TemplateResponse(
        "site/home.html",
        {
            "request": request,
            "lang": lang,
            "i18n": i18n,
            "news": news,
            "items": items,
            "settings": settings,
        },
    )


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request, db=Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    return templates.TemplateResponse(
        "site/about.html",
        {
            "request": request,
            "lang": lang,
            "i18n": i18n,
            "settings": settings,
        },
    )


@router.get("/portfolio", response_class=HTMLResponse)
async def portfolio_index(request: Request, db=Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    categories = []
    return templates.TemplateResponse(
        "site/portfolio_index.html",
        {
            "request": request,
            "lang": lang,
            "i18n": i18n,
            "categories": categories,
            "settings": settings,
        },
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db=Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    return templates.TemplateResponse(
        "site/contact.html",
        {
            "request": request,
            "lang": lang,
            "i18n": i18n,
            "settings": settings,
        },
    )

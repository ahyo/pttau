from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.models.carousel import CarouselItem, CarouselItemTR
from app.models.page import Page
from app.services.content import get_page_by_slug, get_page_tr
from app.services.i18n_db import DBI18n
from app.db import get_db
from app.config import settings
from sqlalchemy.orm import Session
from app.services.menu import get_menu_tree
from app.ui import active_lang, common_ctx, get_footer_data, templates

router = APIRouter()


@router.get("/sitemap.xml", response_class=PlainTextResponse)
async def sitemap(request: Request, db: Session = Depends(get_db)):
    pages = db.execute(select(Page).where(Page.is_published == True)).scalars().all()
    base = settings.BASE_URL.rstrip("/")
    urls = [f"<url><loc>{base}/</loc></url>"]
    for p in pages:
        urls.append(f"<url><loc>{base}/p/{p.slug}</loc></url>")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return PlainTextResponse(body, media_type="application/xml")


def _ctx(request: Request, db: Session):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    return lang, i18n


def pick_tr(db, item_id, lang):
    tr = db.execute(
        select(CarouselItemTR).where(
            CarouselItemTR.item_id == item_id, CarouselItemTR.lang == lang
        )
    ).scalar_one_or_none()
    if tr:
        return tr
    # fallback
    for f in [settings.DEFAULT_LANG, "en", "id", "ar"]:
        tr = db.execute(
            select(CarouselItemTR).where(
                CarouselItemTR.item_id == item_id, CarouselItemTR.lang == f
            )
        ).scalar_one_or_none()
        if tr:
            return tr
    return None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    lang = active_lang
    items = (
        db.execute(
            select(CarouselItem)
            .where(CarouselItem.is_active == True)
            .order_by(CarouselItem.sort_order.asc(), CarouselItem.id.desc())
        )
        .scalars()
        .all()
    )

    slides = []
    for it in items:
        tr = db.execute(
            select(CarouselItemTR).where(
                CarouselItemTR.item_id == it.id, CarouselItemTR.lang == lang
            )
        ).scalar_one_or_none()
        slides.append({"item": it, "tr": tr})

    return templates.TemplateResponse(
        "site/home.html", {"request": request, "slides": slides}
    )


# custom form
@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("site/contact.html", {"request": request})


# B) Generic: semua slug lain di-handle di sini (/p/{slug})
@router.get("/{slug}", response_class=HTMLResponse)
async def page_by_slug(slug: str, request: Request, db: Session = Depends(get_db)):
    lang, i18n = _ctx(request, db)
    page = get_page_by_slug(db, slug)
    if not page:
        raise HTTPException(404)
    tr = get_page_tr(db, page.id, lang)
    return templates.TemplateResponse(
        "site/page.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
                "page": page,
                "tr": tr,
            },
        ),
    )

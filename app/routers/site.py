from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import select

from app.models.carousel import CarouselItem
from app.models.page import Page
from app.services.content import get_page_by_slug
from app.db import get_db
from app.config import settings
from sqlalchemy.orm import Session
from app.ui import active_lang, common_ctx, templates

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


def get_section(db: Session, slug: str):
    return db.execute(select(Page).where(Page.slug == slug)).scalar_one_or_none()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    lang = active_lang(request)

    section_home_1 = get_section(db, "section-home-1")
    section_home_2 = get_section(db, "section-home-2")
    highlight = get_section(db, "section-highlight")
    kapabilitas = get_section(db, "section-kapabilitas")

    items = (
        db.execute(
            select(CarouselItem)
            .where(CarouselItem.is_active == True)
            .order_by(CarouselItem.sort_order.asc(), CarouselItem.id.desc())
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "site/home.html",
        {
            "request": request,
            "slides": items,
            "highlight_section": highlight,
            "kapabilitas_section": kapabilitas,
            "section_home_1": section_home_1,
            "section_home_2": section_home_2,
        },
    )


# custom form
@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("site/contact.html", {"request": request})


# B) Generic: semua slug lain di-handle di sini (/p/{slug})
@router.get("/{slug}", response_class=HTMLResponse)
async def page_by_slug(slug: str, request: Request, db: Session = Depends(get_db)):
    page = get_page_by_slug(db, slug)
    if not page:
        raise HTTPException(404)
    return templates.TemplateResponse(
        "site/page.html",
        common_ctx(
            request,
            {
                "page": page,
            },
        ),
    )

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models.product import Product, ProductTR
from app.services.content import get_page_by_slug, get_page_tr
from app.services.i18n_db import DBI18n
from app.ui import common_ctx, templates

router = APIRouter(tags=["catalog"])


def pick_translation(product: Product, lang: str) -> Optional[ProductTR]:
    for candidate in [lang, settings.DEFAULT_LANG, "en", "id"]:
        for tr in product.translations:
            if tr.lang == candidate:
                return tr
    return None


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_list(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)

    page = get_page_by_slug(db, "catalog")
    if not page:
        raise HTTPException(404)
    tr = get_page_tr(db, page.id, lang)
    msg = request.query_params.get("msg", "")

    products = (
        db.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.created_at.desc())
            .options(selectinload(Product.translations))
        )
        .scalars()
        .all()
    )

    product_cards = []
    for product in products:
        tr = pick_translation(product, lang)
        product_cards.append({"product": product, "tr": tr})

    return templates.TemplateResponse(
        "site/catalog.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
                "products": product_cards,
                "msg": msg,
                "tr": tr,
            },
        ),
    )


@router.get("/catalog/{slug}", response_class=HTMLResponse)
async def catalog_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)

    msg = request.query_params.get("msg", "")

    product = db.execute(
        select(Product)
        .where(Product.slug == slug, Product.is_active == True)
        .options(selectinload(Product.translations))
    ).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404)

    tr = pick_translation(product, lang)

    return templates.TemplateResponse(
        "site/product_detail.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
                "product": product,
                "tr": tr,
                "msg": msg,
            },
        ),
    )

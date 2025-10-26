from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models.product import Product
from app.services.content import get_page_by_slug
from app.ui import common_ctx, templates

router = APIRouter(tags=["catalog"])


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_list(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)

    page = get_page_by_slug(db, "catalog")
    if not page:
        raise HTTPException(404)
    msg = request.query_params.get("msg", "")

    products = (
        db.execute(
            select(Product)
            .options(selectinload(Product.translations))
            .where(Product.is_active == True)
            .order_by(Product.created_at.desc())
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "site/catalog.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "products": products,
                "msg": msg,
                "page": page,
            },
        ),
    )


@router.get("/catalog/{slug}", response_class=HTMLResponse)
async def catalog_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)

    msg = request.query_params.get("msg", "")

    product = db.execute(
        select(Product)
        .options(selectinload(Product.translations))
        .where(Product.slug == slug, Product.is_active == True)
    ).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        "site/product_detail.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "product": product,
                "msg": msg,
            },
        ),
    )

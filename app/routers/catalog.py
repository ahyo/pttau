from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models.product import Product
from app.models.brand import Brand
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

    brand_slug = request.query_params.get("brand")
    brand_filter = None
    if brand_slug:
        brand_filter = db.execute(
            select(Brand).where(Brand.slug == brand_slug)
        ).scalar_one_or_none()

    products_query = (
        select(Product)
        .options(selectinload(Product.translations), selectinload(Product.brand))
        .where(Product.is_active == True)
        .order_by(Product.created_at.desc())
    )
    if brand_filter:
        products_query = products_query.where(Product.brand_id == brand_filter.id)

    products = (
        db.execute(products_query)
        .scalars()
        .all()
    )

    brands = db.execute(select(Brand).order_by(Brand.name.asc())).scalars().all()

    return templates.TemplateResponse(
        "site/catalog.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "products": products,
                "msg": msg,
                "page": page,
                "brands": brands,
                "active_brand": brand_filter,
            },
        ),
    )


@router.get("/catalog/{slug}", response_class=HTMLResponse)
async def catalog_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)

    msg = request.query_params.get("msg", "")

    product = db.execute(
        select(Product)
        .options(selectinload(Product.translations), selectinload(Product.brand))
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

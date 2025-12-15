import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.db import get_db
from app.models.brand import Brand
from app.ui import common_ctx, templates

router = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)


def require_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _normalize_slug(value: str, fallback: str = "brand") -> str:
    normalized = slugify(value or "")
    return normalized or fallback


def _slug_exists(db: Session, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(Brand.id).where(Brand.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Brand.id != exclude_id)
    return db.execute(stmt).scalar_one_or_none() is not None


@router.get("/admin/brands", response_class=HTMLResponse)
async def admin_brand_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    msg = request.query_params.get("msg", "")
    brands = db.execute(select(Brand).order_by(Brand.name.asc())).scalars().all()
    return templates.TemplateResponse(
        "admin/brands/list.html",
        common_ctx(
            request,
            {
                "brands": brands,
                "msg": msg,
            },
        ),
    )


@router.get("/admin/brands/create", response_class=HTMLResponse)
async def admin_brand_create_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    return templates.TemplateResponse(
        "admin/brands/form.html",
        common_ctx(
            request,
            {
                "mode": "create",
                "brand": None,
                "form_data": {},
            },
        ),
    )


@router.post("/admin/brands/create")
async def admin_brand_create(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(""),
    slug: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    desired_slug = (slug or "").strip() or (name or "").strip() or "brand"
    brand_slug = _normalize_slug(desired_slug)

    if _slug_exists(db, brand_slug):
        return templates.TemplateResponse(
            "admin/brands/form.html",
            common_ctx(
                request,
                {
                    "mode": "create",
                    "brand": None,
                    "form_data": {"name": name, "slug": slug},
                    "error": "Slug sudah digunakan. Gunakan slug lain.",
                },
            ),
            status_code=400,
        )

    brand = Brand(slug=brand_slug, name=(name or brand_slug).strip())
    db.add(brand)
    db.commit()

    return RedirectResponse("/admin/brands?msg=Created", status_code=302)


@router.get("/admin/brands/{brand_id}/edit", response_class=HTMLResponse)
async def admin_brand_edit_form(
    brand_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    brand = db.get(Brand, brand_id)
    if not brand:
        return RedirectResponse("/admin/brands?msg=Not%20found", status_code=302)

    return templates.TemplateResponse(
        "admin/brands/form.html",
        common_ctx(
            request,
            {
                "mode": "edit",
                "brand": brand,
                "form_data": {},
            },
        ),
    )


@router.post("/admin/brands/{brand_id}/edit")
async def admin_brand_edit(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(""),
    slug: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    brand = db.get(Brand, brand_id)
    if not brand:
        return RedirectResponse("/admin/brands?msg=Not%20found", status_code=302)

    desired_slug = (slug or "").strip() or (name or "").strip() or brand.slug
    brand_slug = _normalize_slug(desired_slug, fallback=brand.slug)

    if _slug_exists(db, brand_slug, exclude_id=brand.id):
        return templates.TemplateResponse(
            "admin/brands/form.html",
            common_ctx(
                request,
                {
                    "mode": "edit",
                    "brand": brand,
                    "form_data": {"name": name, "slug": slug},
                    "error": "Slug sudah digunakan. Gunakan slug lain.",
                },
            ),
            status_code=400,
        )

    brand.slug = brand_slug
    brand.name = (name or brand.name or brand.slug).strip()
    db.commit()

    return RedirectResponse("/admin/brands?msg=Updated", status_code=302)


@router.post("/admin/brands/{brand_id}/delete")
async def admin_brand_delete(
    brand_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    brand = db.get(Brand, brand_id)
    if brand:
        db.delete(brand)
        db.commit()

    return RedirectResponse("/admin/brands?msg=Deleted", status_code=302)

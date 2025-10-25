from decimal import Decimal, InvalidOperation
import os

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.db import get_db
from app.models.product import Product
from app.ui import common_ctx, templates

router = APIRouter(tags=["admin"])


def require_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal("0.00")


@router.get("/admin/products", response_class=HTMLResponse)
async def admin_product_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    msg = request.query_params.get("msg", "")

    products = (
        db.execute(select(Product).order_by(Product.created_at.desc()))
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "admin/products/list.html",
        common_ctx(
            request,
            {
                "products": products,
                "msg": msg,
            },
        ),
    )


@router.get("/admin/products/create", response_class=HTMLResponse)
async def admin_product_create_form(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    return templates.TemplateResponse(
        "admin/products/form.html",
        common_ctx(
            request,
            {
                "mode": "create",
                "product": None,
                "form_data": {},
            },
        ),
    )


def _normalize_slug(value: str) -> str:
    normalized = slugify(value or "")
    return normalized or "product"


def _slug_exists(
    db: Session, slug: str, exclude_product_id: int | None = None
) -> bool:
    stmt = select(Product.id).where(Product.slug == slug)
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    return db.execute(stmt).scalar_one_or_none() is not None


@router.post("/admin/products/create")
async def admin_product_create(
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    price: str = Form("0"),
    stock: int = Form(0),
    image_url: str = Form(""),
    image_file: UploadFile = File(None),
    is_active: str = Form("on"),
    name: str = Form(""),
    short_description: str = Form(""),
    description: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    desired_slug = (
        (slug or "").strip()
        or (name or "").strip()
        or "product"
    )
    product_slug = _normalize_slug(desired_slug)
    if _slug_exists(db, product_slug):
        return templates.TemplateResponse(
            "admin/products/form.html",
            common_ctx(
                request,
                {
                    "mode": "create",
                    "product": None,
                    "form_data": {
                        "name": name,
                        "short_description": short_description,
                        "description": description,
                        "price": price,
                        "stock": stock,
                        "image_url": image_url,
                        "is_active": is_active,
                    },
                    "error": "Slug sudah digunakan. Gunakan slug lain.",
                },
            ),
            status_code=400,
        )

    media_path = _save_upload(image_file)
    cleaned_image_url = (image_url or "").strip()
    product = Product(
        slug=product_slug,
        price=_parse_decimal(price),
        stock=stock,
        image_url=media_path or (cleaned_image_url or None),
        is_active=is_active == "on",
        name=(name or product_slug).strip(),
        short_description=short_description.strip() or None,
        description=description,
    )
    db.add(product)
    db.flush()

    db.commit()

    return RedirectResponse("/admin/products?msg=Created", status_code=302)


@router.get("/admin/products/{product_id}/edit", response_class=HTMLResponse)
async def admin_product_edit_form(
    product_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/admin/products?msg=Not%20found", status_code=302)

    return templates.TemplateResponse(
        "admin/products/form.html",
        common_ctx(
            request,
            {
                "mode": "edit",
                "product": product,
                "form_data": {},
            },
        ),
    )


@router.post("/admin/products/{product_id}/edit")
async def admin_product_edit(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    price: str = Form("0"),
    stock: int = Form(0),
    image_url: str = Form(""),
    image_file: UploadFile = File(None),
    is_active: str = Form("off"),
    name: str = Form(""),
    short_description: str = Form(""),
    description: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/admin/products?msg=Not%20found", status_code=302)

    desired_slug = (
        (slug or "").strip()
        or product.slug
        or (name or "").strip()
        or "product"
    )
    new_slug = _normalize_slug(desired_slug)
    if _slug_exists(db, new_slug, exclude_product_id=product.id):
        return templates.TemplateResponse(
            "admin/products/form.html",
            common_ctx(
                request,
                {
                    "mode": "edit",
                    "product": product,
                    "form_data": {
                        "name": name,
                        "short_description": short_description,
                        "description": description,
                        "price": price,
                        "stock": stock,
                        "image_url": image_url,
                        "is_active": is_active,
                    },
                    "error": "Slug sudah digunakan. Gunakan slug lain.",
                },
            ),
            status_code=400,
        )
    product.slug = new_slug
    product.price = _parse_decimal(price)
    product.stock = stock
    media_path = _save_upload(image_file)
    cleaned_image_url = (image_url or "").strip()
    if media_path:
        product.image_url = media_path
    elif cleaned_image_url:
        product.image_url = cleaned_image_url
    product.is_active = is_active == "on"
    product.name = (name or product.name or product.slug).strip()
    product.short_description = short_description.strip() or None
    product.description = description

    db.commit()

    return RedirectResponse("/admin/products?msg=Updated", status_code=302)


@router.post("/admin/products/{product_id}/delete")
async def admin_product_delete(
    product_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    product = db.get(Product, product_id)
    if product:
        db.delete(product)
        db.commit()

    return RedirectResponse("/admin/products?msg=Deleted", status_code=302)
UPLOAD_DIR = "app/static/uploads/products"


def _save_upload(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = upload.filename.replace(" ", "_")
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as out:
        out.write(upload.file.read())
    return "/" + path.split("/", 1)[1]

from decimal import Decimal, InvalidOperation
import os

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.db import get_db
from app.models.product import Product, ProductTR
from app.services.i18n_db import DBI18n
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

    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)

    return templates.TemplateResponse(
        "admin/products/form.html",
        common_ctx(
            request,
            {
                "mode": "create",
                "i18n": i18n,
                "lang": lang,
                "translations": {},
            },
        ),
    )


def _set_translation(db: Session, product: Product, lang: str, data: dict):
    text_fields = [data.get("name"), data.get("short_description"), data.get("description")]
    if not any(filter(None, text_fields)):
        return

    existing = next((tr for tr in product.translations if tr.lang == lang), None)
    if existing:
        existing.name = data.get("name") or existing.name
        existing.short_description = data.get("short_description")
        existing.description = data.get("description")
    else:
        db.add(
            ProductTR(
                product_id=product.id,
                lang=lang,
                name=data.get("name") or product.slug,
                short_description=data.get("short_description"),
                description=data.get("description"),
            )
        )


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
    id_name: str = Form(""),
    id_short_description: str = Form(""),
    id_description: str = Form(""),
    en_name: str = Form(""),
    en_short_description: str = Form(""),
    en_description: str = Form(""),
    ar_name: str = Form(""),
    ar_short_description: str = Form(""),
    ar_description: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    product_slug = slugify(slug or id_name or en_name or "product")

    media_path = _save_upload(image_file)

    product = Product(
        slug=product_slug,
        price=_parse_decimal(price),
        stock=stock,
        image_url=(media_path or image_url.strip() or None),
        is_active=is_active == "on",
    )
    db.add(product)
    db.flush()

    _set_translation(
        db,
        product,
        "id",
        {
            "name": id_name.strip(),
            "short_description": id_short_description.strip(),
            "description": id_description,
        },
    )
    _set_translation(
        db,
        product,
        "en",
        {
            "name": en_name.strip(),
            "short_description": en_short_description.strip(),
            "description": en_description,
        },
    )
    _set_translation(
        db,
        product,
        "ar",
        {
            "name": ar_name.strip(),
            "short_description": ar_short_description.strip(),
            "description": ar_description,
        },
    )

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

    translations = {tr.lang: tr for tr in product.translations}
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)

    return templates.TemplateResponse(
        "admin/products/form.html",
        common_ctx(
            request,
            {
                "mode": "edit",
                "product": product,
                "translations": translations,
                "i18n": i18n,
                "lang": lang,
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
    id_name: str = Form(""),
    id_short_description: str = Form(""),
    id_description: str = Form(""),
    en_name: str = Form(""),
    en_short_description: str = Form(""),
    en_description: str = Form(""),
    ar_name: str = Form(""),
    ar_short_description: str = Form(""),
    ar_description: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/admin/products?msg=Not%20found", status_code=302)

    product.slug = slugify(slug or product.slug or id_name or en_name)
    product.price = _parse_decimal(price)
    product.stock = stock
    media_path = _save_upload(image_file)
    product.image_url = media_path or (image_url.strip() or None)
    product.is_active = is_active == "on"

    _set_translation(
        db,
        product,
        "id",
        {
            "name": id_name.strip(),
            "short_description": id_short_description.strip(),
            "description": id_description,
        },
    )
    _set_translation(
        db,
        product,
        "en",
        {
            "name": en_name.strip(),
            "short_description": en_short_description.strip(),
            "description": en_description,
        },
    )
    _set_translation(
        db,
        product,
        "ar",
        {
            "name": ar_name.strip(),
            "short_description": ar_short_description.strip(),
            "description": ar_description,
        },
    )

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


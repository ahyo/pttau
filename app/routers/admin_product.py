import logging
from decimal import Decimal, InvalidOperation
import os

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify

from app.db import get_db
from app.models.product import Product, ProductTranslation
from app.ui import common_ctx, templates
from app.services.translator import (
    translate_payload,
    SUPPORTED_LANGS,
    LANG_LABELS,
    collect_translation_inputs,
)

router = APIRouter(tags=["admin"])


logger = logging.getLogger(__name__)


def require_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal("0.00")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _auto_translate_fields(payload: dict[str, str | None]) -> dict[str, dict[str, str | None]]:
    try:
        return translate_payload(payload, SUPPORTED_LANGS)
    except Exception as exc:  # pragma: no cover - translation service might be unavailable
        logger.warning("Auto translation unavailable, reusing source text: %s", exc)
        return {lang: dict(payload) for lang in SUPPORTED_LANGS}


def _ensure_translation_records(
    product: Product,
    translations_data: dict[str, dict[str, str | None]],
    db: Session,
) -> None:
    existing = {tr.lang: tr for tr in product.translations}
    for lang in SUPPORTED_LANGS:
        data = translations_data.get(lang, {})
        tr = existing.get(lang)
        if not tr:
            tr = ProductTranslation(product=product, lang=lang)
            db.add(tr)

        name_val = _clean_text(data.get("name")) or product.name
        tr.name = name_val

        short_val = _clean_text(data.get("short_description"))
        tr.short_description = short_val if short_val is not None else product.short_description

        desc_val = _clean_text(data.get("description"))
        tr.description = desc_val if desc_val is not None else product.description


def _build_translation_form(product: Product | None = None) -> dict[str, dict[str, str]]:
    form: dict[str, dict[str, str]] = {}
    for lang in SUPPORTED_LANGS:
        if product:
            tr = product.get_translation(lang)
            form[lang] = {
                "name": (tr.name if tr and tr.name else ""),
                "short_description": (tr.short_description if tr and tr.short_description else ""),
                "description": (tr.description if tr and tr.description else ""),
            }
        else:
            form[lang] = {"name": "", "short_description": "", "description": ""}
    return form


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
                "translation_form": _build_translation_form(),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
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

    form_payload = await request.form()
    translation_form = collect_translation_inputs(
        form_payload, ["name", "short_description", "description"]
    )

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
                "translation_form": translation_form,
                "translation_langs": [
                        {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                        for lang in SUPPORTED_LANGS
                    ],
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

    payload = {
        "name": product.name,
        "short_description": product.short_description,
        "description": product.description,
    }
    auto_data = _auto_translate_fields(payload)
    merged: dict[str, dict[str, str | None]] = {}
    for lang in SUPPORTED_LANGS:
        manual = translation_form.get(lang, {})
        auto = auto_data.get(lang, {})
        merged_lang: dict[str, str | None] = {}
        for field, auto_value in auto.items():
            manual_value = manual.get(field) if isinstance(manual, dict) else None
            value = manual_value.strip() if isinstance(manual_value, str) else manual_value
            merged_lang[field] = value if value else auto_value
        merged[lang] = merged_lang
    _ensure_translation_records(product, merged, db)

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
                "translation_form": _build_translation_form(product),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
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

    form_payload = await request.form()
    translation_form = collect_translation_inputs(
        form_payload, ["name", "short_description", "description"]
    )

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
                    "translation_form": translation_form,
                    "translation_langs": [
                        {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                        for lang in SUPPORTED_LANGS
                    ],
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

    auto_payload = {
        "name": product.name,
        "short_description": product.short_description,
        "description": product.description,
    }
    auto_translations = _auto_translate_fields(auto_payload)
    merged_translations: dict[str, dict[str, str | None]] = {}
    for lang in SUPPORTED_LANGS:
        manual = translation_form.get(lang, {})
        auto = auto_translations.get(lang, {})
        merged: dict[str, str | None] = {}
        for field in ["name", "short_description", "description"]:
            manual_val = manual.get(field)
            value = manual_val.strip() if isinstance(manual_val, str) else manual_val
            if value:
                merged[field] = value
            else:
                merged[field] = auto.get(field)
        merged_translations[lang] = merged

    _ensure_translation_records(product, merged_translations, db)

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

import logging
import os

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from slugify import slugify

from app.db import get_db
from app.models.service import Service, ServiceTranslation
from app.services.translator import (
    LANG_LABELS,
    SUPPORTED_LANGS,
    collect_translation_inputs,
    translate_payload,
)
from app.ui import common_ctx, templates

router = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)


def require_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _normalize_slug(value: str, fallback: str = "layanan") -> str:
    normalized = slugify(value or "")
    return normalized or fallback


def _slug_exists(db: Session, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(Service.id).where(Service.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Service.id != exclude_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def _auto_translate_fields(
    payload: dict[str, str | None]
) -> dict[str, dict[str, str | None]]:
    try:
        return await translate_payload(payload, SUPPORTED_LANGS)
    except Exception as exc:  # pragma: no cover - translation service might be unavailable
        logger.warning("Auto translation unavailable, reusing source text: %s", exc)
        return {lang: dict(payload) for lang in SUPPORTED_LANGS}


def _ensure_translation_records(
    service: Service,
    translations_data: dict[str, dict[str, str | None]],
    db: Session,
) -> None:
    existing = {tr.lang: tr for tr in service.translations}
    for lang in SUPPORTED_LANGS:
        data = translations_data.get(lang, {})
        tr = existing.get(lang)
        if not tr:
            tr = ServiceTranslation(service=service, lang=lang)
            db.add(tr)

        title_val = _clean_text(data.get("title")) or service.title
        tr.title = title_val

        desc_val = _clean_text(data.get("description"))
        tr.description = desc_val if desc_val is not None else service.description

        content_val = _clean_text(data.get("content"))
        tr.content = content_val if content_val is not None else service.content


def _build_translation_form(service: Service | None = None) -> dict[str, dict[str, str]]:
    form: dict[str, dict[str, str]] = {}
    for lang in SUPPORTED_LANGS:
        if service:
            tr = service.get_translation(lang)
            form[lang] = {
                "title": tr.title if tr and tr.title else "",
                "description": tr.description if tr and tr.description else "",
                "content": tr.content if tr and tr.content else "",
            }
        else:
            form[lang] = {"title": "", "description": "", "content": ""}
    return form


@router.get("/admin/services", response_class=HTMLResponse)
async def admin_service_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    msg = request.query_params.get("msg", "")
    services = (
        db.execute(
            select(Service)
            .options(selectinload(Service.translations))
            .order_by(Service.created_at.desc())
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "admin/services/list.html",
        common_ctx(
            request,
            {
                "services": services,
                "msg": msg,
            },
        ),
    )


@router.get("/admin/services/create", response_class=HTMLResponse)
async def admin_service_create_form(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    return templates.TemplateResponse(
        "admin/services/form.html",
        common_ctx(
            request,
            {
                "mode": "create",
                "service": None,
                "form_data": {},
                "translation_form": _build_translation_form(),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
            },
        ),
    )


@router.post("/admin/services/create")
async def admin_service_create(
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    image_url: str = Form(""),
    image_file: UploadFile = File(None),
    is_active: str = Form("on"),
    title: str = Form(""),
    description: str = Form(""),
    content: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    form_payload = await request.form()
    translation_form = collect_translation_inputs(
        form_payload, ["title", "description", "content"]
    )

    desired_slug = (slug or "").strip() or (title or "").strip() or "layanan"
    service_slug = _normalize_slug(desired_slug)
    if _slug_exists(db, service_slug):
        return templates.TemplateResponse(
            "admin/services/form.html",
            common_ctx(
                request,
                {
                    "mode": "create",
                    "service": None,
                    "form_data": {
                        "title": title,
                        "description": description,
                        "content": content,
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
    service = Service(
        slug=service_slug,
        title=(title or service_slug).strip(),
        description=description.strip() or None,
        content=content,
        image_url=media_path or (cleaned_image_url or None),
        is_active=is_active == "on",
    )
    db.add(service)
    db.flush()

    payload = {
        "title": service.title,
        "description": service.description,
        "content": service.content,
    }
    auto_data = await _auto_translate_fields(payload)
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
    _ensure_translation_records(service, merged, db)

    db.commit()

    return RedirectResponse("/admin/services?msg=Created", status_code=302)


@router.get("/admin/services/{service_id}/edit", response_class=HTMLResponse)
async def admin_service_edit_form(
    service_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    service = db.execute(
        select(Service)
        .options(selectinload(Service.translations))
        .where(Service.id == service_id)
    ).scalar_one_or_none()
    if not service:
        return RedirectResponse("/admin/services?msg=Not%20found", status_code=302)

    return templates.TemplateResponse(
        "admin/services/form.html",
        common_ctx(
            request,
            {
                "mode": "edit",
                "service": service,
                "form_data": {},
                "translation_form": _build_translation_form(service),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
            },
        ),
    )


@router.post("/admin/services/{service_id}/edit")
async def admin_service_edit(
    service_id: int,
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    image_url: str = Form(""),
    image_file: UploadFile = File(None),
    is_active: str = Form("on"),
    title: str = Form(""),
    description: str = Form(""),
    content: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    service = db.execute(
        select(Service)
        .options(selectinload(Service.translations))
        .where(Service.id == service_id)
    ).scalar_one_or_none()
    if not service:
        return RedirectResponse("/admin/services?msg=Not%20found", status_code=302)

    form_payload = await request.form()
    translation_form = collect_translation_inputs(
        form_payload, ["title", "description", "content"]
    )

    desired_slug = (slug or "").strip() or (title or "").strip() or service.slug
    service_slug = _normalize_slug(desired_slug, fallback=service.slug)
    if _slug_exists(db, service_slug, exclude_id=service.id):
        return templates.TemplateResponse(
            "admin/services/form.html",
            common_ctx(
                request,
                {
                    "mode": "edit",
                    "service": service,
                    "form_data": {
                        "slug": slug,
                        "title": title,
                        "description": description,
                        "content": content,
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
    if media_path:
        service.image_url = media_path
    elif cleaned_image_url:
        service.image_url = cleaned_image_url

    service.slug = service_slug
    service.title = (title or service.title or service.slug).strip()
    service.description = description.strip() or None
    service.content = content
    service.is_active = is_active == "on"

    auto_payload = {
        "title": service.title,
        "description": service.description,
        "content": service.content,
    }
    auto_translations = await _auto_translate_fields(auto_payload)
    merged_translations: dict[str, dict[str, str | None]] = {}
    for lang in SUPPORTED_LANGS:
        manual = translation_form.get(lang, {})
        auto = auto_translations.get(lang, {})
        merged: dict[str, str | None] = {}
        for field in ["title", "description", "content"]:
            manual_val = manual.get(field)
            value = manual_val.strip() if isinstance(manual_val, str) else manual_val
            if value:
                merged[field] = value
            else:
                merged[field] = auto.get(field)
        merged_translations[lang] = merged

    _ensure_translation_records(service, merged_translations, db)

    db.commit()

    return RedirectResponse("/admin/services?msg=Updated", status_code=302)


@router.post("/admin/services/{service_id}/delete")
async def admin_service_delete(
    service_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    service = db.get(Service, service_id)
    if service:
        db.delete(service)
        db.commit()

    return RedirectResponse("/admin/services?msg=Deleted", status_code=302)


UPLOAD_DIR = "app/static/uploads/services"


def _save_upload(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = upload.filename.replace(" ", "_")
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as out:
        out.write(upload.file.read())
    return "/" + path.split("/", 1)[1]

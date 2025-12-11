# app/routers/admin_menu.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models.menu import MenuItem, MenuItemTranslation
from app.ui import common_ctx
from app.services.translator import (
    translate_payload,
    SUPPORTED_LANGS,
    LANG_LABELS,
    collect_translation_inputs,
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _ensure_menu_translations(item: MenuItem, data: dict[str, str | None], db: Session):
    existing = {tr.lang: tr for tr in item.translations}
    for lang in SUPPORTED_LANGS:
        value = _clean(data.get(lang))
        if value is None:
            value = item.label
        tr = existing.get(lang)
        if tr:
            if value is not None:
                tr.label = value
            continue
        db.add(
            MenuItemTranslation(menu_item=item, lang=lang, label=value or item.label)
        )


async def _auto_menu_translations(label: str | None) -> dict[str, str | None]:
    payload = {"label": label or ""}
    translated = await translate_payload(payload, SUPPORTED_LANGS)
    return {lang: data.get("label") for lang, data in translated.items()}


def _build_translation_form(item: MenuItem | None = None) -> dict[str, str]:
    form: dict[str, str] = {}
    if not item:
        for lang in SUPPORTED_LANGS:
            form[lang] = ""
        return form
    for lang in SUPPORTED_LANGS:
        tr = item.get_translation(lang)
        form[lang] = tr.label if tr and tr.label else ""
    return form


# LIST
@router.get("/admin/menu", response_class=HTMLResponse)
async def menu_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    items = (
        db.execute(
            select(MenuItem).order_by(
                MenuItem.sort_order.asc(),
                MenuItem.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    rows = []
    for it in items:
        rows.append(
            {
                "id": it.id,
                "parent_id": it.parent_id,
                "position": it.position,
                "url": it.url,
                "is_external": it.is_external,
                "requires_admin": it.requires_admin,
                "sort_order": it.sort_order,
                "active": it.is_active,
                "label": it.label or "(no label)",
            }
        )
    # opsi parent utk form create
    parents = (
        db.execute(
            select(MenuItem)
            .where(MenuItem.parent_id == None)
            .order_by(MenuItem.sort_order, MenuItem.id)
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        "admin/menu_list.html",
        common_ctx(
            request,
            {
                "items": rows,
                "parents": parents,
            },
        ),
    )


# CREATE (POST dari form di menu_list)
@router.post("/admin/menu/create")
async def menu_create(
    request: Request,
    db: Session = Depends(get_db),
    parent_id: str = Form(""),
    position: str = Form("header"),
    url: str = Form(...),
    is_external: str = Form("off"),
    target: str = Form("_self"),
    sort_order: int = Form(0),
    is_active: str = Form("on"),
    requires_admin: str = Form("off"),
    icon: str = Form(""),
    label: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    try:
        pid = int(parent_id) if parent_id.strip() else None
    except:
        pid = None

    item = MenuItem(
        parent_id=pid,
        position=position,
        url=url,
        is_external=(is_external == "on"),
        target=target or ("_blank" if is_external == "on" else "_self"),
        sort_order=sort_order,
        is_active=(is_active == "on"),
        requires_admin=(requires_admin == "on"),
        icon=icon or None,
        label=label or "Menu",
    )
    db.add(item)
    db.flush()

    translations = await _auto_menu_translations(item.label)
    _ensure_menu_translations(item, translations, db)

    db.commit()
    return RedirectResponse("/admin/menu?msg=created", 302)


# EDIT FORM
@router.get("/admin/menu/{mid}/edit", response_class=HTMLResponse)
async def menu_edit_form(mid: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    item = db.get(MenuItem, mid)
    if not item:
        return RedirectResponse("/admin/menu?msg=not_found", 302)
    parents = (
        db.execute(
            select(MenuItem)
            .where(MenuItem.parent_id == None, MenuItem.id != mid)
            .order_by(MenuItem.sort_order, MenuItem.id)
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        "admin/menu_form.html",
        {
            "request": request,
            "item": item,
            "parents": parents,
            "translation_form": _build_translation_form(item),
            "translation_langs": [
                {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                for lang in SUPPORTED_LANGS
            ],
        },
    )


# EDIT POST
@router.post("/admin/menu/{mid}/edit")
async def menu_edit(
    mid: int,
    request: Request,
    db: Session = Depends(get_db),
    parent_id: str = Form(""),
    position: str = Form("header"),
    url: str = Form(...),
    is_external: str = Form("off"),
    target: str = Form("_self"),
    sort_order: int = Form(0),
    is_active: str = Form("on"),
    requires_admin: str = Form("off"),
    icon: str = Form(""),
    label: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    item = db.get(MenuItem, mid)
    if not item:
        return RedirectResponse("/admin/menu?msg=not_found", 302)
    form_payload = await request.form()
    translation_form = collect_translation_inputs(form_payload, ["label"])

    try:
        pid = int(parent_id) if parent_id.strip() else None
    except:
        pid = None

    item.parent_id = pid
    item.position = position
    item.url = url
    item.is_external = is_external == "on"
    item.target = target or ("_blank" if is_external == "on" else "_self")
    item.sort_order = sort_order
    item.is_active = is_active == "on"
    item.requires_admin = requires_admin == "on"
    item.icon = icon or None
    item.label = label or item.label or "Menu"

    auto_translations = await _auto_menu_translations(item.label)
    merged: dict[str, str | None] = {}
    for lang in SUPPORTED_LANGS:
        manual_val = translation_form.get(lang, {}).get("label")
        cleaned = _clean(manual_val)
        merged[lang] = cleaned if cleaned else auto_translations.get(lang)
    _ensure_menu_translations(item, merged, db)

    db.commit()
    return RedirectResponse("/admin/menu?msg=updated", 302)


# DELETE
@router.post("/admin/menu/{mid}/delete")
async def menu_delete(mid: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    item = db.get(MenuItem, mid)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/admin/menu?msg=deleted", 302)

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


def _fetch_all_menu_items(db: Session) -> list[MenuItem]:
    return (
        db.execute(
            select(MenuItem).order_by(
                MenuItem.parent_id.asc(),
                MenuItem.sort_order.asc(),
                MenuItem.id.asc(),
            )
        )
        .scalars()
        .all()
    )


def _collect_descendant_ids(root_id: int, by_parent: dict[int | None, list[MenuItem]]):
    descendants: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        for child in by_parent.get(current, []):
            if child.id not in descendants:
                descendants.add(child.id)
                stack.append(child.id)
    return descendants


def _build_parent_options(
    items: list[MenuItem], exclude_ids: set[int] | None = None
) -> list[dict[str, str | int]]:
    by_parent: dict[int | None, list[MenuItem]] = {}
    for it in items:
        by_parent.setdefault(it.parent_id, []).append(it)

    for children in by_parent.values():
        children.sort(key=lambda x: (x.sort_order, x.id))

    options: list[dict[str, str | int]] = []

    def walk(pid: int | None, depth: int = 0):
        for node in by_parent.get(pid, []):
            if exclude_ids and node.id in exclude_ids:
                continue
            prefix = ("  " * depth) + ("- " if depth else "")
            options.append({"id": node.id, "label": f"{prefix}{node.label}"})
            walk(node.id, depth + 1)

    walk(None)
    return options


# LIST
@router.get("/admin/menu", response_class=HTMLResponse)
async def menu_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    items = _fetch_all_menu_items(db)

    parent_lookup = {it.id: it for it in items}
    rows = []
    for it in items:
        rows.append(
            {
                "id": it.id,
                "parent_id": it.parent_id,
                "parent_label": parent_lookup.get(it.parent_id).label
                if it.parent_id
                else None,
                "position": it.position,
                "url": it.url,
                "is_external": it.is_external,
                "requires_admin": it.requires_admin,
                "sort_order": it.sort_order,
                "active": it.is_active,
                "label": it.label or "(no label)",
            }
        )
    parent_options = _build_parent_options(items)
    return templates.TemplateResponse(
        "admin/menu_list.html",
        common_ctx(
            request,
            {
                "items": rows,
                "parent_options": parent_options,
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
    items = _fetch_all_menu_items(db)
    by_parent: dict[int | None, list[MenuItem]] = {}
    for it in items:
        by_parent.setdefault(it.parent_id, []).append(it)
    excluded = _collect_descendant_ids(mid, by_parent)
    excluded.add(mid)
    parent_options = _build_parent_options(items, excluded)
    return templates.TemplateResponse(
        "admin/menu_form.html",
        {
            "request": request,
            "item": item,
            "parent_options": parent_options,
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

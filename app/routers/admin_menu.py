# app/routers/admin_menu.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models.menu import MenuItem, MenuItemTR
from app.services.i18n_db import DBI18n
from app.services.menu import get_menu_tree
from app.ui import common_ctx, get_footer_data

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["admin"])
LANGS = ["id", "en", "ar"]


def require_admin(request: Request):
    return request.session.get("admin")


# LIST
@router.get("/admin/menu", response_class=HTMLResponse)
async def menu_list(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    footer_data = get_footer_data(db, lang)
    admin = request.session.get("admin")
    header_menu = get_menu_tree(db, lang, "header", admin_logged=bool(admin))
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

    # build dict label per item utk tampilan list
    def label_for(item, lang="id"):
        trs = {tr.lang: tr.label for tr in item.translations}
        return trs.get(lang) or trs.get("en") or trs.get("id") or "(no label)"

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
                "label_id": label_for(it, "id"),
                "label_en": label_for(it, "en"),
                "label_ar": label_for(it, "ar"),
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
                "i18n": i18n,
                "footer_sections": footer_data,
                "header_menu": header_menu,
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
    id_label: str = Form(""),
    en_label: str = Form(""),
    ar_label: str = Form(""),
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
    )
    db.add(item)
    db.flush()

    for lang, label in [("id", id_label), ("en", en_label), ("ar", ar_label)]:
        if label:
            db.add(MenuItemTR(item_id=item.id, lang=lang, label=label))

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
    trs = {tr.lang: tr for tr in item.translations}
    return templates.TemplateResponse(
        "admin/menu_form.html",
        {"request": request, "item": item, "parents": parents, "trs": trs},
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
    id_label: str = Form(""),
    en_label: str = Form(""),
    ar_label: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    item = db.get(MenuItem, mid)
    if not item:
        return RedirectResponse("/admin/menu?msg=not_found", 302)

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

    existing = {tr.lang: tr for tr in item.translations}
    for lang, label in [("id", id_label), ("en", en_label), ("ar", ar_label)]:
        tr = existing.get(lang)
        if tr:
            tr.label = label or tr.label
        else:
            if label:
                db.add(MenuItemTR(item_id=item.id, lang=lang, label=label))

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

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.db import get_db
from app.models.footer import FooterSection, FooterSectionTR, FooterLink, FooterLinkTR
from app.services.i18n_db import DBI18n
from app.ui import templates, get_footer_data, common_ctx
from app.config import settings

router = APIRouter(tags=["admin"])

LANGS = ["id", "en", "ar"]


def require_admin(request: Request):
    return request.session.get("admin")


@router.get("/admin/footer", response_class=HTMLResponse)
def footer_sections_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    sections = (
        db.execute(
            select(FooterSection)
            .options(selectinload(FooterSection.translations))  # <- muat translasi
            .order_by(FooterSection.sort_order.asc(), FooterSection.id.asc())
        )
        .scalars()
        .all()
    )

    rows = []
    for s in sections:
        names = {tr.lang: tr.name for tr in (s.translations or [])}
        rows.append(
            {
                "id": s.id,
                "sort_order": s.sort_order,
                "name_id": names.get("id"),
                "name_en": names.get("en"),
                "name_ar": names.get("ar"),
            }
        )

    return templates.TemplateResponse(
        "admin/footer_sections.html", {"request": request, "sections": rows}
    )


# Create section
@router.post("/admin/footer/section/create")
async def section_create(
    request: Request,
    db: Session = Depends(get_db),
    sort_order: int = Form(0),
    id_name: str = Form(""),
    en_name: str = Form(""),
    ar_name: str = Form(""),
):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    s = FooterSection(sort_order=sort_order)
    db.add(s)
    db.flush()
    for lang, name in [("id", id_name), ("en", en_name), ("ar", ar_name)]:
        if name:
            db.add(FooterSectionTR(section_id=s.id, lang=lang, name=name))
    db.commit()
    return RedirectResponse("/admin/footer", 302)


# Manage links
@router.get("/admin/footer/{sid}/links", response_class=HTMLResponse)
async def footer_links(sid: int, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    section = db.get(FooterSection, sid)
    links = (
        db.execute(
            select(FooterLink)
            .where(FooterLink.section_id == sid)
            .order_by(FooterLink.sort_order)
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        "admin/footer_links.html",
        common_ctx(request, {"section": section, "links": links, "i18n": i18n}),
    )


@router.post("/admin/footer/{sid}/links/create")
async def link_create(
    sid: int,
    request: Request,
    db: Session = Depends(get_db),
    icon: str = Form(""),
    url: str = Form(""),
    sort_order: int = Form(0),
    id_label: str = Form(""),
    en_label: str = Form(""),
    ar_label: str = Form(""),
):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    link = FooterLink(section_id=sid, icon=icon, url=url, sort_order=sort_order)
    db.add(link)
    db.flush()

    for lang, label in [("id", id_label), ("en", en_label), ("ar", ar_label)]:
        if label:
            db.add(FooterLinkTR(link_id=link.id, lang=lang, label=label))
    db.commit()

    return RedirectResponse(f"/admin/footer/{sid}/links", 302)


@router.get("/admin/footer/section/{sid}/edit", response_class=HTMLResponse)
async def section_edit_form(sid: int, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    section = db.get(FooterSection, sid)
    if not section:
        return RedirectResponse("/admin/footer?msg=Not%20found", 302)

    # buat dict translasi: {"id": FooterSectionTR|None, ...}
    tr_map = {tr.lang: tr for tr in section.translations}

    return templates.TemplateResponse(
        "admin/footer_section_edit.html",
        common_ctx(request, {"section": section, "trs": tr_map, "i18n": i18n}),
    )


@router.post("/admin/footer/section/{sid}/edit")
async def section_edit(
    sid: int,
    request: Request,
    db: Session = Depends(get_db),
    code: str = Form(""),
    sort_order: int = Form(0),
    is_active: str = Form("off"),
    id_name: str = Form(""),
    en_name: str = Form(""),
    ar_name: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    if not section:
        return RedirectResponse("/admin/footer?msg=Not%20found", 302)

    section.code = code or None
    section.sort_order = sort_order
    section.is_active = is_active == "on"

    # Upsert translasi
    existing = {tr.lang: tr for tr in section.translations}
    for lang, val in [("id", id_name), ("en", en_name), ("ar", ar_name)]:
        tr = existing.get(lang)
        if tr:
            tr.name = val or tr.name
            # jika ingin bisa kosongkan: tr.name = val
        else:
            if val:
                db.add(FooterSectionTR(section_id=section.id, lang=lang, name=val))

    db.commit()
    return RedirectResponse("/admin/footer?msg=Updated", 302)


# =====================================================================
# EDIT FOOTER LINK
# =====================================================================


@router.get("/admin/footer/{sid}/links/{lid}/edit", response_class=HTMLResponse)
async def link_edit_form(
    sid: int, lid: int, request: Request, db: Session = Depends(get_db)
):
    lang = getattr(request.state, "lang", settings.DEFAULT_LANG)
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    link = db.get(FooterLink, lid)
    if not section or not link or link.section_id != section.id:
        return RedirectResponse(f"/admin/footer/{sid}/links?msg=Not%20found", 302)

    tr_map = {tr.lang: tr for tr in link.translations}

    return templates.TemplateResponse(
        "admin/footer_link_edit.html",
        common_ctx(
            request, {"section": section, "link": link, "trs": tr_map, "i18n": i18n}
        ),
    )


@router.post("/admin/footer/{sid}/links/{lid}/edit")
async def link_edit(
    sid: int,
    lid: int,
    request: Request,
    db: Session = Depends(get_db),
    icon: str = Form(""),
    url: str = Form(""),
    sort_order: int = Form(0),
    is_active: str = Form("off"),
    id_label: str = Form(""),
    en_label: str = Form(""),
    ar_label: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    link = db.get(FooterLink, lid)
    if not section or not link or link.section_id != section.id:
        return RedirectResponse(f"/admin/footer/{sid}/links?msg=Not%20found", 302)

    # update properti link
    link.icon = icon or None
    link.url = url or None
    link.sort_order = sort_order
    link.is_active = is_active == "on"

    # upsert translasi label
    existing = {tr.lang: tr for tr in link.translations}
    for lang, label in [("id", id_label), ("en", en_label), ("ar", ar_label)]:
        tr = existing.get(lang)
        if tr:
            # jika label kosong dan kamu ingin kosongkan, pakai: tr.label = label
            if label:
                tr.label = label
        else:
            if label:
                db.add(FooterLinkTR(link_id=link.id, lang=lang, label=label))

    db.commit()
    return RedirectResponse(f"/admin/footer/{sid}/links?msg=Updated", 302)

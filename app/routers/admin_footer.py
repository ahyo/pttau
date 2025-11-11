from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models.footer import (
    FooterSection,
    FooterLink,
    FooterSectionTranslation,
    FooterLinkTranslation,
)
from app.ui import templates, common_ctx
from app.services.translator import (
    translate_payload,
    SUPPORTED_LANGS,
    LANG_LABELS,
    collect_translation_inputs,
)

router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _auto_section(name: str | None):
    payload = {"name": name}
    return translate_payload(payload, SUPPORTED_LANGS)


def _ensure_section_translations(
    section: FooterSection,
    translations: dict[str, str | None],
    db: Session,
):
    existing = {tr.lang: tr for tr in section.translations}
    for lang in SUPPORTED_LANGS:
        value = (
            _clean(translations.get(lang)) if isinstance(translations, dict) else None
        )
        if value is None:
            value = section.name
        tr = existing.get(lang)
        if tr:
            if value is not None:
                tr.name = value
            continue
        db.add(FooterSectionTranslation(section=section, lang=lang, name=value))


def _build_section_translation_form(
    section: FooterSection | None = None,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for lang in SUPPORTED_LANGS:
        if section:
            tr = section.get_translation(lang)
            result[lang] = tr.name if tr and tr.name else ""
        else:
            result[lang] = ""
    return result


async def _auto_link(html: str | None):
    payload = {"html_content": html}
    return await translate_payload(payload, SUPPORTED_LANGS)


def _ensure_link_translations(
    link: FooterLink,
    translations: dict[str, str | None],
    db: Session,
):
    existing = {tr.lang: tr for tr in link.translations}
    for lang in SUPPORTED_LANGS:
        value = translations.get(lang)
        cleaned = _clean(value)
        if cleaned is None:
            cleaned = link.html_content
        tr = existing.get(lang)
        if tr:
            if cleaned is not None:
                tr.html_content = cleaned
            continue
        db.add(FooterLinkTranslation(link=link, lang=lang, html_content=cleaned))


def _build_link_translation_form(link: FooterLink | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for lang in SUPPORTED_LANGS:
        if link:
            tr = link.get_translation(lang)
            result[lang] = tr.html_content if tr and tr.html_content else ""
        else:
            result[lang] = ""
    return result


@router.get("/admin/footer", response_class=HTMLResponse)
def footer_sections_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    sections = (
        db.execute(
            select(FooterSection).order_by(
                FooterSection.sort_order.asc(), FooterSection.id.asc()
            )
        )
        .scalars()
        .all()
    )

    rows = [
        {
            "id": s.id,
            "sort_order": s.sort_order,
            "name": s.name,
            "is_active": s.is_active,
        }
        for s in sections
    ]

    return templates.TemplateResponse(
        "admin/footer_sections.html", {"request": request, "sections": rows}
    )


# Create section
@router.post("/admin/footer/section/create")
async def section_create(
    request: Request,
    db: Session = Depends(get_db),
    sort_order: int = Form(0),
    name: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    s = FooterSection(sort_order=sort_order, name=name.strip() or "Section")
    db.add(s)
    db.flush()

    auto_translations = _auto_section(s.name)
    mapped = {lang: data.get("name") for lang, data in auto_translations.items()}
    _ensure_section_translations(s, mapped, db)

    db.commit()
    return RedirectResponse("/admin/footer", 302)


# Manage links
@router.get("/admin/footer/{sid}/links", response_class=HTMLResponse)
async def footer_links(sid: int, request: Request, db: Session = Depends(get_db)):
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
        common_ctx(request, {"section": section, "links": links}),
    )


@router.post("/admin/footer/{sid}/links/create")
async def link_create(
    sid: int,
    request: Request,
    db: Session = Depends(get_db),
    sort_order: int = Form(0),
    html_content: str = Form(""),
    is_active: str = Form("on"),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    link = FooterLink(
        section_id=sid,
        sort_order=sort_order,
        html_content=html_content.strip(),
        is_active=is_active == "on",
    )
    db.add(link)
    db.flush()

    auto_translations = _auto_link(link.html_content)
    mapped = {
        lang: data.get("html_content") for lang, data in auto_translations.items()
    }
    _ensure_link_translations(link, mapped, db)

    db.commit()

    return RedirectResponse(f"/admin/footer/{sid}/links", 302)


@router.get("/admin/footer/section/{sid}/edit", response_class=HTMLResponse)
async def section_edit_form(sid: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)
    section = db.get(FooterSection, sid)
    if not section:
        return RedirectResponse("/admin/footer?msg=Not%20found", 302)

    return templates.TemplateResponse(
        "admin/footer_section_edit.html",
        common_ctx(
            request,
            {
                "section": section,
                "translation_form": _build_section_translation_form(section),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
            },
        ),
    )


@router.post("/admin/footer/section/{sid}/edit")
async def section_edit(
    sid: int,
    request: Request,
    db: Session = Depends(get_db),
    sort_order: int = Form(0),
    is_active: str = Form("off"),
    name: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    if not section:
        return RedirectResponse("/admin/footer?msg=Not%20found", 302)

    section.sort_order = sort_order
    section.is_active = is_active == "on"
    section.name = name.strip() or section.name

    form_payload = await request.form()
    raw_translations = collect_translation_inputs(form_payload, ["name"])
    manual_map = {
        lang: _clean(raw_translations.get(lang, {}).get("name"))
        for lang in SUPPORTED_LANGS
    }
    auto_map_raw = _auto_section(section.name)
    auto_map = {
        lang: _clean(data.get("name")) if isinstance(data, dict) else None
        for lang, data in auto_map_raw.items()
    }
    merged_map = {
        lang: (manual_map.get(lang) or auto_map.get(lang) or section.name)
        for lang in SUPPORTED_LANGS
    }
    _ensure_section_translations(section, merged_map, db)

    db.commit()
    return RedirectResponse("/admin/footer?msg=Updated", 302)


# =====================================================================
# EDIT FOOTER LINK
# =====================================================================


@router.get("/admin/footer/{sid}/links/{lid}/edit", response_class=HTMLResponse)
async def link_edit_form(
    sid: int, lid: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    link = db.get(FooterLink, lid)
    if not section or not link or link.section_id != section.id:
        return RedirectResponse(f"/admin/footer/{sid}/links?msg=Not%20found", 302)

    return templates.TemplateResponse(
        "admin/footer_link_edit.html",
        common_ctx(
            request,
            {
                "section": section,
                "link": link,
                "translation_form": _build_link_translation_form(link),
                "translation_langs": [
                    {"code": lang, "label": LANG_LABELS.get(lang, lang.upper())}
                    for lang in SUPPORTED_LANGS
                ],
            },
        ),
    )


@router.post("/admin/footer/{sid}/links/{lid}/edit")
async def link_edit(
    sid: int,
    lid: int,
    request: Request,
    db: Session = Depends(get_db),
    sort_order: int = Form(0),
    is_active: str = Form("off"),
    html_content: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login", 302)

    section = db.get(FooterSection, sid)
    link = db.get(FooterLink, lid)
    if not section or not link or link.section_id != section.id:
        return RedirectResponse(f"/admin/footer/{sid}/links?msg=Not%20found", 302)

    # update properti link
    link.sort_order = sort_order
    link.is_active = is_active == "on"
    link.html_content = html_content.strip()

    form_payload = await request.form()
    raw_translations = collect_translation_inputs(form_payload, ["html_content"])
    manual_map = {
        lang: _clean(raw_translations.get(lang, {}).get("html_content"))
        for lang in SUPPORTED_LANGS
    }
    auto_map_raw = await _auto_link(link.html_content)
    print(auto_map_raw)
    auto_map = {
        lang: _clean(data.get("html_content")) if isinstance(data, dict) else None
        for lang, data in auto_map_raw.items()
    }
    merged_map = {
        lang: (manual_map.get(lang) or auto_map.get(lang) or link.html_content)
        for lang in SUPPORTED_LANGS
    }
    _ensure_link_translations(link, merged_map, db)

    # db.commit()
    return RedirectResponse(f"/admin/footer/{sid}/links?msg=Updated", 302)

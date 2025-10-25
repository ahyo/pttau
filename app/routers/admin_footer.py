from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models.footer import FooterSection, FooterLink
from app.ui import templates, common_ctx

router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


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
        common_ctx(request, {"section": section}),
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
        common_ctx(request, {"section": section, "link": link}),
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

    db.commit()
    return RedirectResponse(f"/admin/footer/{sid}/links?msg=Updated", 302)

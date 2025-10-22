# app/ui.py
from fastapi.templating import Jinja2Templates
from app.config import settings
from sqlalchemy import select
from app.models.footer import FooterSection, FooterSectionTR, FooterLink, FooterLinkTR


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = settings


def common_ctx(request, extra: dict | None = None):
    base = {
        "request": request,
        "lang": getattr(request.state, "lang", settings.DEFAULT_LANG),
        "admin": getattr(request.state, "admin", request.session.get("admin")),
        "user": getattr(request.state, "user", request.session.get("user")),
        "cart_count": getattr(request.state, "cart_count", 0),
    }
    if extra:
        base.update(extra)
    return base


def get_footer_data(db, lang: str):
    sections = (
        db.execute(
            select(FooterSection)
            .where(FooterSection.is_active == True)
            .order_by(FooterSection.sort_order)
        )
        .scalars()
        .all()
    )
    footer_data = []
    for sec in sections:
        tr_name = db.execute(
            select(FooterSectionTR.name).where(
                FooterSectionTR.section_id == sec.id, FooterSectionTR.lang == lang
            )
        ).scalar_one_or_none()
        name = (
            tr_name
            or db.execute(
                select(FooterSectionTR.name).where(
                    FooterSectionTR.section_id == sec.id, FooterSectionTR.lang == "en"
                )
            ).scalar_one_or_none()
        )
        links = (
            db.execute(
                select(FooterLink)
                .where(FooterLink.section_id == sec.id, FooterLink.is_active == True)
                .order_by(FooterLink.sort_order)
            )
            .scalars()
            .all()
        )
        link_data = []
        for l in links:
            lbl = db.execute(
                select(FooterLinkTR.label).where(
                    FooterLinkTR.link_id == l.id, FooterLinkTR.lang == lang
                )
            ).scalar_one_or_none()
            link_data.append(
                {"icon": l.icon, "url": l.url, "label": lbl or "(no label)"}
            )
        footer_data.append({"name": name, "links": link_data})
    return footer_data


def active_lang(request):
    from app.config import settings

    return getattr(request.state, "lang", settings.DEFAULT_LANG)

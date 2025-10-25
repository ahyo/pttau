# app/ui.py
from fastapi.templating import Jinja2Templates
from app.config import settings
from sqlalchemy import select
from app.models.footer import FooterSection, FooterLink


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


def get_footer_data(db, lang: str | None = None):
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
            link_data.append(
                {
                    "id": l.id,
                    "html": l.html_content or "",
                    "is_active": l.is_active,
                }
            )
        footer_data.append({"name": sec.name, "links": link_data})
    return footer_data


def active_lang(request):
    from app.config import settings

    return getattr(request.state, "lang", settings.DEFAULT_LANG)

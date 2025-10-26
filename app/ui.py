# app/ui.py
from fastapi.templating import Jinja2Templates
from app.config import settings
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.footer import FooterSection, FooterLink
from app.services.translator import (
    ALL_LANGS,
    SUPPORTED_LANGS,
    LANG_LABELS,
    LANG_FLAGS,
)


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = settings


LANGUAGE_OPTIONS = [
    {
        "code": code,
        "label": LANG_LABELS.get(code, code.upper()),
        "flag": LANG_FLAGS.get(code, "🌐"),
    }
    for code in ALL_LANGS
]



def localized_attr(entity, lang: str, field: str):
    if entity is None:
        return ""
    base_value = getattr(entity, field, None)
    if not lang or lang == "id":
        return base_value
    getter = getattr(entity, "get_translation", None)
    if not callable(getter):
        return base_value
    translation = getter(lang)
    if translation:
        translated_value = getattr(translation, field, None)
        if translated_value:
            return translated_value
    return base_value


def product_text(product, lang: str, field: str):
    return localized_attr(product, lang, field)


templates.env.globals["product_text"] = product_text
templates.env.globals["localized_attr"] = localized_attr
templates.env.globals["language_options"] = LANGUAGE_OPTIONS
templates.env.globals["translation_languages"] = SUPPORTED_LANGS


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
            .options(
                selectinload(FooterSection.translations),
                selectinload(FooterSection.links).selectinload(FooterLink.translations),
            )
            .where(FooterSection.is_active == True)
            .order_by(FooterSection.sort_order)
        )
        .scalars()
        .all()
    )
    footer_data = []
    for sec in sections:
        link_data = []
        for l in sorted(sec.links, key=lambda x: (x.sort_order, x.id)):
            if not l.is_active:
                continue
            link_data.append(
                {
                    "id": l.id,
                    "html": localized_attr(l, lang, "html_content") or "",
                    "is_active": l.is_active,
                }
            )
        footer_data.append({
            "name": localized_attr(sec, lang, "name") or sec.name,
            "links": link_data,
        })
    return footer_data


def active_lang(request):
    from app.config import settings

    return getattr(request.state, "lang", settings.DEFAULT_LANG)

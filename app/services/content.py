# app/services/content.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.page import Page, PageTR

FALLBACK_ORDER = lambda current: [current, "id", "en", "ar"]  # prioritas sederhana


def get_page_by_slug(db: Session, slug: str):
    return db.execute(
        select(Page).where(Page.slug == slug, Page.is_published == True)
    ).scalar_one_or_none()


def get_page_tr(db: Session, page_id: int, lang: str):
    for code in FALLBACK_ORDER(lang):
        tr = db.execute(
            select(PageTR).where(PageTR.page_id == page_id, PageTR.lang == code)
        ).scalar_one_or_none()
        if tr:
            return tr
    return None  # benar-benar tidak ada

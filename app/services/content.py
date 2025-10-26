# app/services/content.py
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.page import Page


def get_page_by_slug(db: Session, slug: str):
    return db.execute(
        select(Page)
        .options(selectinload(Page.translations))
        .where(Page.slug == slug, Page.is_published == True)
    ).scalar_one_or_none()

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.page import Page
from app.services.content import get_page_by_slug
from app.ui import common_ctx, templates

router = APIRouter(tags=["articles"])

ARTICLE_PREFIX = "artikel-"


def _normalize_article_slug(slug: str) -> str:
    cleaned = (slug or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith(ARTICLE_PREFIX):
        return cleaned
    return f"{ARTICLE_PREFIX}{cleaned}"


def _article_filters():
    return (Page.is_published == True, Page.slug.like(f"{ARTICLE_PREFIX}%"))


@router.get("/artikel", response_class=HTMLResponse)
async def article_list(request: Request, db: Session = Depends(get_db), page: int = 1):
    per_page = 9
    page = max(page, 1)

    total = (
        db.execute(select(func.count(Page.id)).where(*_article_filters()))
        .scalar()
        or 0
    )
    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    if page > total_pages:
        page = total_pages

    items = (
        db.execute(
            select(Page)
            .options(selectinload(Page.translations))
            .where(*_article_filters())
            .order_by(Page.id.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
        .scalars()
        .all()
    )

    page_info = get_page_by_slug(db, "artikel")

    pagination = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }

    return templates.TemplateResponse(
        "site/articles.html",
        common_ctx(
            request,
            {
                "page": page_info,
                "articles": items,
                "pagination": pagination,
            },
        ),
    )


@router.get("/artikel/{slug}", response_class=HTMLResponse)
async def article_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    normalized = _normalize_article_slug(slug)
    if not normalized:
        raise HTTPException(status_code=404)

    article = (
        db.execute(
            select(Page)
            .options(selectinload(Page.translations))
            .where(Page.slug == normalized, Page.is_published == True)
        )
        .scalar_one_or_none()
    )

    if not article:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        "site/article_detail.html",
        common_ctx(
            request,
            {
                "article": article,
            },
        ),
    )

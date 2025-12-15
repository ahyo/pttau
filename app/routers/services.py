from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.service import Service
from app.services.content import get_page_by_slug
from app.ui import common_ctx, templates

router = APIRouter(tags=["services"])


def _active_services(db: Session):
    return (
        db.execute(
            select(Service)
            .options(selectinload(Service.translations))
            .where(Service.is_active == True)
            .order_by(Service.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/layanan", response_class=HTMLResponse)
async def service_list(request: Request, db: Session = Depends(get_db)):
    page = get_page_by_slug(db, "layanan")
    services = _active_services(db)
    return templates.TemplateResponse(
        "site/services.html",
        common_ctx(
            request,
            {
                "page": page,
                "services": services,
            },
        ),
    )


@router.get("/layanan/{slug}", response_class=HTMLResponse)
async def service_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", None)
    service = db.execute(
        select(Service)
        .options(selectinload(Service.translations))
        .where(Service.slug == slug, Service.is_active == True)
    ).scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=404)

    other_services = [s for s in _active_services(db) if s.id != service.id]

    return templates.TemplateResponse(
        "site/service_detail.html",
        common_ctx(
            request,
            {
                "service": service,
                "services": other_services,
                "lang": lang,
            },
        ),
    )

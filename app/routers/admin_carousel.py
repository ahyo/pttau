from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
import os, shutil

from app.db import get_db
from app.config import settings
from app.models.carousel import CarouselItem

from app.ui import templates

router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


UPLOAD_DIR = "app/static/uploads"  # pastikan folder ini writable di server


def save_upload(file: UploadFile | None) -> str | None:
    if not file or not file.filename:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    name = file.filename.replace(" ", "_")
    dst = os.path.join(UPLOAD_DIR, name)
    with open(dst, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return (
        "/" + dst.split("/", 1)[1]
    )  # path relatif utk web: /app/static/uploads/.. → /static/uploads/..


@router.get("/admin/carousel", response_class=HTMLResponse)
async def list_items(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    items = (
        db.execute(
            select(CarouselItem).order_by(
                CarouselItem.sort_order.asc(), CarouselItem.id.desc()
            )
        )
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        "admin/carousel_list.html",
        {
            "request": request,
            "items": items,
        },
    )


@router.get("/admin/carousel/create", response_class=HTMLResponse)
async def create_form(request: Request, db: Session = Depends(get_db)):

    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    return templates.TemplateResponse(
        "admin/carousel_form.html",
        {
            "request": request,
            "mode": "create",
            "form_data": {},
        },
    )


@router.post("/admin/carousel/create")
async def create_item(
    request: Request,
    db: Session = Depends(get_db),
    media_type: str = Form("image"),
    sort_order: int = Form(0),
    is_active: str = Form("on"),
    # file upload
    media_file: UploadFile = File(None),
    poster_file: UploadFile = File(None),
    title: str = Form(""),
    subtitle: str = Form(""),
    cta_text: str = Form(""),
    cta_url: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    media_path = save_upload(media_file)
    poster_path = save_upload(poster_file)
    item = CarouselItem(
        media_type=media_type,
        media_path=media_path or "",
        poster_path=poster_path,
        is_active=(is_active == "on"),
        sort_order=sort_order,
        title=title.strip() or None,
        subtitle=subtitle.strip() or None,
        cta_text=cta_text.strip() or None,
        cta_url=cta_url.strip() or None,
    )
    db.add(item)

    db.commit()
    return RedirectResponse(url="/admin/carousel", status_code=302)


@router.get("/admin/carousel/{item_id}/edit", response_class=HTMLResponse)
async def edit_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", 302)

    item = db.get(CarouselItem, item_id)
    if not item:
        return RedirectResponse("/admin/carousel?msg=Not%20found", 302)

    return templates.TemplateResponse(
        "admin/carousel_form.html",
        {
            "request": request,
            "mode": "edit",
            "item": item,
            "form_data": {},
        },
    )


from typing import Optional


@router.post("/admin/carousel/{item_id}/edit")
async def edit_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    media_type: str = Form("image"),
    sort_order: int = Form(0),
    is_active: str = Form("off"),
    media_file: UploadFile = File(None),
    poster_file: UploadFile = File(None),
    title: Optional[str] = Form(None),
    subtitle: Optional[str] = Form(None),
    cta_text: Optional[str] = Form(None),
    cta_url: Optional[str] = Form(None),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", 302)

    item = db.get(CarouselItem, item_id)
    if not item:
        return RedirectResponse("/admin/carousel?msg=Not%20found", 302)

    item.media_type = media_type
    if new_media := save_upload(media_file):
        item.media_path = new_media
    if new_poster := save_upload(poster_file):
        item.poster_path = new_poster
    item.is_active = is_active == "on"
    item.sort_order = sort_order
    if title is not None:
        item.title = title.strip() or None
    if subtitle is not None:
        item.subtitle = subtitle.strip() or None
    if cta_text is not None:
        item.cta_text = cta_text.strip() or None
    if cta_url is not None:
        item.cta_url = cta_url.strip() or None

    db.commit()
    return RedirectResponse("/admin/carousel?msg=updated", 302)


@router.post("/admin/carousel/{item_id}/delete")
async def delete_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    item = db.get(CarouselItem, item_id)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/carousel", status_code=302)

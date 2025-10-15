from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
import os, shutil

from app.db import get_db
from app.config import settings
from app.deps import get_session_admin
from app.models.carousel import CarouselItem, CarouselItemTR

from app.services.i18n_db import DBI18n
from app.ui import common_ctx, get_footer_data, templates

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
    # TR
    id_title: str = Form(""),
    id_subtitle: str = Form(""),
    id_cta_text: str = Form(""),
    id_cta_url: str = Form(""),
    en_title: str = Form(""),
    en_subtitle: str = Form(""),
    en_cta_text: str = Form(""),
    en_cta_url: str = Form(""),
    ar_title: str = Form(""),
    ar_subtitle: str = Form(""),
    ar_cta_text: str = Form(""),
    ar_cta_url: str = Form(""),
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
    )
    db.add(item)
    db.flush()

    def add_tr(lang, title, subtitle, cta_text, cta_url):
        if any([title, subtitle, cta_text, cta_url]):
            db.add(
                CarouselItemTR(
                    item_id=item.id,
                    lang=lang,
                    title=title,
                    subtitle=subtitle,
                    cta_text=cta_text,
                    cta_url=cta_url,
                )
            )

    add_tr("id", id_title, id_subtitle, id_cta_text, id_cta_url)
    add_tr("en", en_title, en_subtitle, en_cta_text, en_cta_url)
    add_tr("ar", ar_title, ar_subtitle, ar_cta_text, ar_cta_url)

    db.commit()
    return RedirectResponse(url="/admin/carousel", status_code=302)


@router.get("/admin/carousel/{item_id}/edit", response_class=HTMLResponse)
async def edit_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", 302)

    item = db.get(CarouselItem, item_id)
    if not item:
        return RedirectResponse("/admin/carousel?msg=Not%20found", 302)

    # Map translasi aman
    trs = {tr.lang: tr for tr in (item.translations or [])}
    # print(trs["id"])
    return templates.TemplateResponse(
        "admin/carousel_form.html",
        {
            "request": request,
            "mode": "edit",
            "item": item,
            "trs": trs,
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
    # --- jadikan opsional (None) ---
    id_title: Optional[str] = Form(None),
    id_subtitle: Optional[str] = Form(None),
    id_cta_text: Optional[str] = Form(None),
    id_cta_url: Optional[str] = Form(None),
    en_title: Optional[str] = Form(None),
    en_subtitle: Optional[str] = Form(None),
    en_cta_text: Optional[str] = Form(None),
    en_cta_url: Optional[str] = Form(None),
    ar_title: Optional[str] = Form(None),
    ar_subtitle: Optional[str] = Form(None),
    ar_cta_text: Optional[str] = Form(None),
    ar_cta_url: Optional[str] = Form(None),
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

    def keep(old: Optional[str], new: Optional[str]) -> Optional[str]:
        """Pakai nilai baru hanya jika non-empty setelah strip; kalau None/empty → keep old."""
        if new is None:
            return old
        val = new.strip()
        return val if val != "" else old

    def upsert(lang, title, subtitle, cta_text, cta_url):
        tr = next((t for t in item.translations if t.lang == lang), None)
        if tr:
            tr.title = keep(tr.title, title)
            tr.subtitle = keep(tr.subtitle, subtitle)
            tr.cta_text = keep(tr.cta_text, cta_text)
            tr.cta_url = keep(tr.cta_url, cta_url)
        else:
            # buat baru hanya jika ada minimal satu field non-empty
            vals = [title, subtitle, cta_text, cta_url]
            if any(v and v.strip() for v in vals):
                db.add(
                    CarouselItemTR(
                        item_id=item.id,
                        lang=lang,
                        title=title.strip() if title else None,
                        subtitle=subtitle.strip() if subtitle else None,
                        cta_text=cta_text.strip() if cta_text else None,
                        cta_url=cta_url.strip() if cta_url else None,
                    )
                )

    upsert("id", id_title, id_subtitle, id_cta_text, id_cta_url)
    upsert("en", en_title, en_subtitle, en_cta_text, en_cta_url)
    upsert("ar", ar_title, ar_subtitle, ar_cta_text, ar_cta_url)

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

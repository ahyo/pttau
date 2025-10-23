from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.i18n_db import DBI18n
from slugify import slugify

from app.db import get_db
from app.deps import verify_password, get_session_admin, hash_password
from app.models.page import Page, PageTR
from app.models.user import User
from app.ui import get_footer_data, templates, common_ctx

router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(
    request: Request, msg: str = "", db: Session = Depends(get_db)
):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "msg": msg, "i18n": i18n, "lang": lang}
    )


@router.post("/admin/login")
async def admin_login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    # Note: expects a 'user' table with bcrypt hashes (optional).
    try:
        from app.models.user import User
    except Exception:

        class User:
            pass

        user = None
    else:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    if not user:
        return RedirectResponse(
            url="/admin/login?msg=Invalid%20credentials.", status_code=302
        )
    if not getattr(user, "is_admin", True):
        return RedirectResponse(
            url="/admin/login?msg=Invalid%20credentials..", status_code=302
        )
    # if not verify_password(password, getattr(user, "password_hash", "")):
    #     return RedirectResponse(
    #         url="/admin/login?msg=Invalid%20credentials...", status_code=302
    #     )
    request.session["admin"] = {"id": getattr(user, "id", 1), "username": username}
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("admin", None)
    return RedirectResponse(url="/admin/login?msg=Logged%20out", status_code=302)


@router.get("/admin/password", response_class=HTMLResponse)
async def admin_password_form(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)

    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)

    return templates.TemplateResponse(
        "admin/change_password.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
                "msg": request.query_params.get("msg", ""),
                "err": request.query_params.get("err", ""),
            },
        ),
    )


@router.post("/admin/password")
async def admin_password_update(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)

    admin_session = request.session.get("admin") or {}
    user_id = admin_session.get("id")
    user = db.get(User, user_id) if user_id else None
    if not user:
        request.session.pop("admin", None)
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)

    if not verify_password(current_password, user.password_hash):
        return RedirectResponse(
            url="/admin/password?err=Password%20lama%20salah", status_code=302
        )

    if len(new_password) < 6 or len(new_password) > 128:
        return RedirectResponse(
            url="/admin/password?err=Password%20baru%20harus%206-128%20karakter",
            status_code=302,
        )

    if new_password != confirm_password:
        return RedirectResponse(
            url="/admin/password?err=Konfirmasi%20password%20tidak%20sesuai",
            status_code=302,
        )

    if verify_password(new_password, user.password_hash):
        return RedirectResponse(
            url="/admin/password?err=Password%20baru%20tidak%20boleh%20sama",
            status_code=302,
        )

    user.password_hash = hash_password(new_password)
    db.commit()

    return RedirectResponse(
        url="/admin/password?msg=Password%20berhasil%20diperbarui", status_code=302
    )


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db=Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    return templates.TemplateResponse(
        "admin/dashboard.html", common_ctx(request, {"lang": lang, "i18n": i18n})
    )


@router.get("/admin/pages", response_class=HTMLResponse)
async def pages_list(request: Request, db: Session = Depends(get_db), q: str = ""):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    footer_data = get_footer_data(db, lang)
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    pages = db.query(Page).order_by(Page.id.desc()).all()
    return templates.TemplateResponse(
        "admin/list_page.html",
        common_ctx(
            request,
            {
                "pages": pages,
                "q": q,
                "lang": lang,
                "i18n": i18n,
                "footer_sections": footer_data,
            },
        ),
    )


@router.get("/admin/pages/create", response_class=HTMLResponse)
async def pages_create_form(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    footer_data = get_footer_data(db, lang)
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    return templates.TemplateResponse(
        "admin/form_page.html",
        common_ctx(
            request,
            {
                "mode": "create",
                "lang": lang,
                "i18n": i18n,
                "footer_sections": footer_data,
            },
        ),
    )


@router.post("/admin/pages/create")
async def pages_create(
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    template: str = Form("about"),
    is_published: str = Form("on"),
    id_title: str = Form(""),
    id_excerpt: str = Form(""),
    id_body: str = Form(""),
    en_title: str = Form(""),
    en_excerpt: str = Form(""),
    en_body: str = Form(""),
    ar_title: str = Form(""),
    ar_excerpt: str = Form(""),
    ar_body: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    s = slugify(slug or (id_title or en_title or "page"))
    page = Page(slug=s, template=template, is_published=(is_published == "on"))
    db.add(page)
    db.flush()

    def tr(lang, title, excerpt, body):
        if any([title, excerpt, body]):
            db.add(
                PageTR(
                    page_id=page.id,
                    lang=lang,
                    title=title.strip(),
                    excerpt=excerpt,
                    body=body,
                )
            )

    tr("id", id_title, id_excerpt, id_body)
    tr("en", en_title, en_excerpt, en_body)
    tr("ar", ar_title, ar_excerpt, ar_body)
    db.commit()
    return RedirectResponse(url="/admin/pages", status_code=302)


@router.get("/admin/pages/{page_id}/edit", response_class=HTMLResponse)
async def pages_edit_form(
    page_id: int, request: Request, db: Session = Depends(get_db)
):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    footer_data = get_footer_data(db, lang)
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    page = db.get(Page, page_id)
    if not page:
        return RedirectResponse(url="/admin/pages?msg=Not%20found", status_code=302)
    trs = {tr.lang: tr for tr in page.translations}
    return templates.TemplateResponse(
        "admin/form_page.html",
        common_ctx(
            request,
            {
                "mode": "edit",
                "page": page,
                "trs": trs,
                "lang": lang,
                "i18n": i18n,
                "footer_sections": footer_data,
            },
        ),
    )


@router.post("/admin/pages/{page_id}/edit")
async def pages_edit(
    page_id: int,
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    template: str = Form("about"),
    is_published: str = Form("off"),
    id_title: str = Form(""),
    id_excerpt: str = Form(""),
    id_body: str = Form(""),
    en_title: str = Form(""),
    en_excerpt: str = Form(""),
    en_body: str = Form(""),
    ar_title: str = Form(""),
    ar_excerpt: str = Form(""),
    ar_body: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    page = db.get(Page, page_id)
    if not page:
        return RedirectResponse(url="/admin/pages?msg=Not%20found", status_code=302)
    page.slug = slugify(slug or page.slug)
    page.template = template
    page.is_published = is_published == "on"

    def upsert(lang, title, excerpt, body):
        tr = (
            db.query(PageTR)
            .filter(PageTR.page_id == page.id, PageTR.lang == lang)
            .one_or_none()
        )
        if tr:
            tr.title = title.strip()
            tr.excerpt = excerpt
            tr.body = body
        else:
            if any([title, excerpt, body]):
                db.add(
                    PageTR(
                        page_id=page.id,
                        lang=lang,
                        title=title.strip(),
                        excerpt=excerpt,
                        body=body,
                    )
                )

    upsert("id", id_title, id_excerpt, id_body)
    upsert("en", en_title, en_excerpt, en_body)
    upsert("ar", ar_title, ar_excerpt, ar_body)
    db.commit()
    return RedirectResponse(url="/admin/pages", status_code=302)


@router.post("/admin/pages/{page_id}/delete")
async def pages_delete(page_id: int, request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    page = db.get(Page, page_id)
    if page:
        db.delete(page)
        db.commit()
    return RedirectResponse(url="/admin/pages", status_code=302)

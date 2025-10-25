from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from slugify import slugify

from app.db import get_db
from app.deps import verify_password, hash_password
from app.models.page import Page
from app.models.user import User
from app.ui import templates, common_ctx

router = APIRouter(tags=["admin"])


def require_admin(request: Request):
    return request.session.get("admin")


def _normalize_page_slug(value: str, fallback: str = "page") -> str:
    normalized = slugify(value or "")
    return normalized or fallback


def _page_slug_exists(
    db: Session, slug: str, exclude_page_id: int | None = None
) -> bool:
    stmt = select(Page.id).where(Page.slug == slug)
    if exclude_page_id is not None:
        stmt = stmt.where(Page.id != exclude_page_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def _page_form_response(
    request: Request,
    *,
    mode: str,
    page: Page | None = None,
    form_data: dict | None = None,
    error: str | None = None,
    status_code: int | None = None,
):
    ctx = {
        "mode": mode,
        "page": page,
        "form_data": form_data or {},
        "error": error,
    }
    return templates.TemplateResponse(
        "admin/form_page.html",
        common_ctx(request, ctx),
        status_code=status_code or (400 if error else 200),
    )

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "msg": msg}
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

    return templates.TemplateResponse(
        "admin/change_password.html",
        common_ctx(
            request,
            {
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
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    return templates.TemplateResponse(
        "admin/dashboard.html", common_ctx(request, {})
    )


@router.get("/admin/pages", response_class=HTMLResponse)
async def pages_list(request: Request, db: Session = Depends(get_db), q: str = ""):
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
            },
        ),
    )


@router.get("/admin/pages/create", response_class=HTMLResponse)
async def pages_create_form(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    return templates.TemplateResponse(
        "admin/form_page.html",
        common_ctx(
            request,
            {
                "mode": "create",
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
    title: str = Form(""),
    excerpt: str = Form(""),
    body: str = Form(""),
    meta_title: str = Form(""),
    meta_desc: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    submitted_slug = (slug or "").strip()
    desired_source = submitted_slug or title or "page"
    normalized_slug = _normalize_page_slug(desired_source)

    if _page_slug_exists(db, normalized_slug):
        form_data = {
            "slug": submitted_slug,
            "template": template,
            "is_published": is_published,
            "title": title,
            "excerpt": excerpt,
            "body": body,
            "meta_title": meta_title,
            "meta_desc": meta_desc,
        }
        return _page_form_response(
            request,
            mode="create",
            form_data=form_data,
            error=f"Slug '{normalized_slug}' sudah digunakan. Gunakan slug lain.",
            status_code=400,
        )

    page = Page(
        slug=normalized_slug,
        template=template,
        is_published=(is_published == "on"),
        title=title.strip() or normalized_slug.replace("-", " ").title(),
        excerpt=excerpt.strip() or None,
        body=body,
        meta_title=meta_title.strip() or None,
        meta_desc=meta_desc.strip() or None,
    )
    db.add(page)
    db.commit()
    return RedirectResponse(url="/admin/pages", status_code=302)


@router.get("/admin/pages/{page_id}/edit", response_class=HTMLResponse)
async def pages_edit_form(
    page_id: int, request: Request, db: Session = Depends(get_db)
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    page = db.get(Page, page_id)
    if not page:
        return RedirectResponse(url="/admin/pages?msg=Not%20found", status_code=302)
    return _page_form_response(request, mode="edit", page=page)


@router.post("/admin/pages/{page_id}/edit")
async def pages_edit(
    page_id: int,
    request: Request,
    db: Session = Depends(get_db),
    slug: str = Form(""),
    template: str = Form("about"),
    is_published: str = Form("off"),
    title: str = Form(""),
    excerpt: str = Form(""),
    body: str = Form(""),
    meta_title: str = Form(""),
    meta_desc: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse(url="/admin/login?msg=Please%20login", status_code=302)
    page = db.get(Page, page_id)
    if not page:
        return RedirectResponse(url="/admin/pages?msg=Not%20found", status_code=302)
    submitted_slug = (slug or "").strip()
    desired_source = submitted_slug or title or page.slug or "page"
    normalized_slug = _normalize_page_slug(desired_source, fallback=page.slug or "page")

    if _page_slug_exists(db, normalized_slug, exclude_page_id=page.id):
        form_data = {
            "id": page.id,
            "slug": submitted_slug or page.slug,
            "template": template,
            "is_published": is_published,
            "title": title,
            "excerpt": excerpt,
            "body": body,
            "meta_title": meta_title,
            "meta_desc": meta_desc,
        }
        return _page_form_response(
            request,
            mode="edit",
            page=page,
            form_data=form_data,
            error=f"Slug '{normalized_slug}' sudah digunakan. Gunakan slug lain.",
            status_code=400,
        )

    page.slug = normalized_slug
    page.template = template
    page.is_published = is_published == "on"
    page.title = title.strip() or page.title or page.slug.title()
    page.excerpt = excerpt.strip() or None
    page.body = body
    page.meta_title = meta_title.strip() or None
    page.meta_desc = meta_desc.strip() or None

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

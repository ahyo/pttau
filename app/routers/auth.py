from passlib.hash import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import verify_password
from app.models.user import User
from app.services.i18n_db import DBI18n
from app.ui import common_ctx, templates

router = APIRouter(tags=["auth"])


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    if request.session.get("user"):
        return RedirectResponse("/catalog", status_code=302)

    return templates.TemplateResponse(
        "site/register.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
            },
        ),
    )


@router.post("/register")
async def register_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    username = username.strip().lower()
    if len(username) < 3 or len(password) < 6:
        return RedirectResponse("/register?msg=Invalid%20credentials", status_code=302)
    if len(password.encode("utf-8")) > 72:
        return RedirectResponse(
            "/register?msg=Password%20terlalu%20panjang", status_code=302
        )

    if password != confirm_password:
        return RedirectResponse("/register?msg=Password%20mismatch", status_code=302)

    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        return RedirectResponse("/register?msg=Username%20exists", status_code=302)

    user = User(
        username=username,
        password_hash=bcrypt.hash(password),
        is_admin=False,
    )
    db.add(user)
    db.commit()

    request.session["user"] = {"id": user.id, "username": user.username}

    return RedirectResponse("/catalog?msg=Welcome", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    if request.session.get("user"):
        return RedirectResponse("/catalog", status_code=302)

    return templates.TemplateResponse(
        "site/login.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
            },
        ),
    )


@router.post("/login")
async def login_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    username = username.strip().lower()
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?msg=Invalid%20credentials", status_code=302)

    request.session["user"] = {"id": user.id, "username": user.username}

    return RedirectResponse("/catalog", status_code=302)


@router.get("/logout")
async def logout_user(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/login?msg=Logged%20out", status_code=302)

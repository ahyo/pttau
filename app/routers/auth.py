from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import verify_password, hash_password
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.services.i18n_db import DBI18n
from app.ui import common_ctx, templates

router = APIRouter(tags=["auth"])


def _require_user_session(request: Request) -> dict | None:
    return request.session.get("user")


def _product_name(product: Product | None) -> str:
    if not product:
        return "Produk tidak tersedia"
    translations = getattr(product, "translations", []) or []
    for lang_code in ("id", "en", "ar"):
        tr = next((tran for tran in translations if tran.lang == lang_code), None)
        if tr and tr.name:
            return tr.name
    return product.slug or f"Produk #{product.id}"


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
    email: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    username = username.strip().lower()
    email = email.strip().lower()
    phone_number = phone_number.strip()
    if len(username) < 3 or len(password) < 6:
        return RedirectResponse("/register?msg=Invalid%20credentials", status_code=302)
    if not email or "@" not in email or len(email) > 120:
        return RedirectResponse("/register?msg=Email%20tidak%20valid", status_code=302)
    if not phone_number:
        return RedirectResponse(
            "/register?msg=Nomor%20handphone%20wajib%20diisi", status_code=302
        )
    if len(phone_number) > 30:
        return RedirectResponse(
            "/register?msg=Nomor%20handphone%20terlalu%20panjang", status_code=302
        )
    if len(password) > 128 or len(confirm_password) > 128:
        return RedirectResponse(
            "/register?msg=Password%20terlalu%20panjang", status_code=302
        )

    if password != confirm_password:
        return RedirectResponse("/register?msg=Password%20mismatch", status_code=302)

    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        return RedirectResponse("/register?msg=Username%20exists", status_code=302)
    email_exists = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if email_exists:
        return RedirectResponse("/register?msg=Email%20sudah%20digunakan", status_code=302)

    user = User(
        username=username,
        email=email,
        phone_number=phone_number,
        password_hash=hash_password(password),
        is_admin=False,
    )
    db.add(user)
    db.commit()

    request.session["user"] = {"id": user.id, "username": user.username}

    return RedirectResponse("/catalog?msg=Welcome", status_code=302)


@router.get("/account/orders", response_class=HTMLResponse)
async def account_orders(
    request: Request,
    db: Session = Depends(get_db),
):
    user_session = _require_user_session(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    orders = (
        db.execute(
            select(Cart)
            .where(Cart.user_id == user_session["id"], Cart.status != "open")
            .options(
                selectinload(Cart.items).selectinload(CartItem.product).selectinload(
                    Product.translations
                )
            )
            .order_by(Cart.created_at.desc())
        )
        .scalars()
        .all()
    )

    orders_data = []
    for order in orders:
        total = Decimal("0.00")
        line_items = []
        for item in order.items:
            subtotal = Decimal(item.unit_price or 0) * item.quantity
            total += subtotal
            line_items.append(
                {
                    "name": _product_name(item.product),
                    "quantity": item.quantity,
                    "unit_price": Decimal(item.unit_price or 0),
                    "subtotal": subtotal,
                }
            )

        orders_data.append(
            {
                "order": order,
                "line_items": line_items,
                "total": total,
            }
        )

    return templates.TemplateResponse(
        "site/order_history.html",
        common_ctx(
            request,
            {
                "orders": orders_data,
            },
        ),
    )


@router.get("/account/password", response_class=HTMLResponse)
async def account_password_form(
    request: Request, db: Session = Depends(get_db)
):
    user_session = _require_user_session(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)

    return templates.TemplateResponse(
        "site/change_password.html",
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


@router.post("/account/password")
async def account_password_update(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    user_session = _require_user_session(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    user = db.get(User, user_session["id"])
    if not user:
        request.session.pop("user", None)
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    if not verify_password(current_password, user.password_hash):
        return RedirectResponse(
            "/account/password?err=Password%20lama%20salah", status_code=302
        )

    if len(new_password) < 6 or len(new_password) > 128:
        return RedirectResponse(
            "/account/password?err=Password%20baru%20harus%206-128%20karakter",
            status_code=302,
        )

    if new_password != confirm_password:
        return RedirectResponse(
            "/account/password?err=Konfirmasi%20password%20tidak%20sesuai",
            status_code=302,
        )

    if verify_password(new_password, user.password_hash):
        return RedirectResponse(
            "/account/password?err=Password%20baru%20tidak%20boleh%20sama%20dengan%20password%20lama",
            status_code=302,
        )

    user.password_hash = hash_password(new_password)
    db.commit()

    return RedirectResponse(
        "/account/password?msg=Password%20berhasil%20diperbarui", status_code=302
    )


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

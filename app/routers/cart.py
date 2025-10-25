from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.ui import common_ctx, templates

router = APIRouter(tags=["cart"])


def _ensure_user(request: Request) -> dict | None:
    return request.session.get("user")


def _get_open_cart(db: Session, user_id: int) -> Cart:
    cart = (
        db.execute(
            select(Cart)
            .where(Cart.user_id == user_id, Cart.status == "open")
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
        )
        .scalar_one_or_none()
    )

    if cart:
        return cart

    cart = Cart(user_id=user_id, status="open")
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def _cart_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(f"/cart?msg={message}", status_code=302)


@router.get("/cart", response_class=HTMLResponse)
async def cart_view(request: Request, db: Session = Depends(get_db)):
    user_session = _ensure_user(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    cart = _get_open_cart(db, user_session["id"])

    items = []
    total = Decimal("0.00")
    for item in cart.items:
        product = item.product
        subtotal = Decimal(item.unit_price or 0) * item.quantity
        total += subtotal
        items.append(
            {
                "item": item,
                "product": product,
                "name": product.name,
                "subtotal": subtotal,
            }
        )

    return templates.TemplateResponse(
        "site/cart.html",
        common_ctx(
            request,
            {
                "cart": cart,
                "items": items,
                "total": total,
            },
        ),
    )


@router.post("/cart/add")
async def cart_add(
    request: Request,
    db: Session = Depends(get_db),
    product_id: int = Form(...),
    quantity: int = Form(1),
):
    user_session = _ensure_user(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    product = db.get(Product, product_id)
    if not product or not product.is_active:
        return _cart_redirect("Product%20not%20available")

    if quantity < 1:
        quantity = 1

    cart = _get_open_cart(db, user_session["id"])

    cart_item = next((ci for ci in cart.items if ci.product_id == product.id), None)
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
        db.add(cart_item)

    db.commit()

    referer = request.headers.get("referer") or ""
    fallback = f"/catalog/{product.slug}"
    redirect_target = referer if referer else fallback
    if "?" in redirect_target:
        redirect_target = f"{redirect_target}&msg=Added"
    else:
        redirect_target = f"{redirect_target}?msg=Added"

    return RedirectResponse(redirect_target, status_code=302)


@router.post("/cart/update")
async def cart_update(
    request: Request,
    db: Session = Depends(get_db),
    item_id: int = Form(...),
    quantity: int = Form(...),
):
    user_session = _ensure_user(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    cart = _get_open_cart(db, user_session["id"])
    item = next((ci for ci in cart.items if ci.id == item_id), None)
    if not item:
        return _cart_redirect("Item%20missing")

    if quantity <= 0:
        db.delete(item)
    else:
        item.quantity = quantity

    db.commit()

    return _cart_redirect("Updated")


@router.post("/cart/remove")
async def cart_remove(
    request: Request,
    db: Session = Depends(get_db),
    item_id: int = Form(...),
):
    user_session = _ensure_user(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    cart = _get_open_cart(db, user_session["id"])
    item = next((ci for ci in cart.items if ci.id == item_id), None)
    if not item:
        return _cart_redirect("Item%20missing")

    db.delete(item)
    db.commit()

    return _cart_redirect("Removed")


@router.post("/cart/checkout")
async def cart_checkout(request: Request, db: Session = Depends(get_db)):
    user_session = _ensure_user(request)
    if not user_session:
        return RedirectResponse("/login?msg=Login%20required", status_code=302)

    cart = _get_open_cart(db, user_session["id"])
    if not cart.items:
        return _cart_redirect("Cart%20empty")

    cart.status = "pending"
    db.commit()

    return RedirectResponse("/cart?msg=Checkout%20submitted", status_code=302)

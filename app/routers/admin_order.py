from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.ui import common_ctx, templates

router = APIRouter(tags=["admin"])


def require_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _product_display(product: Product) -> str:
    if not product:
        return "Unknown product"

    translations = getattr(product, "translations", []) or []
    for lang_code in ("id", "en", "ar"):
        tr = next((tran for tran in translations if tran.lang == lang_code), None)
        if tr and tr.name:
            return tr.name

    return product.slug or f"Product #{product.id}"


@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_list(request: Request, db: Session = Depends(get_db)):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    orders = (
        db.execute(
            select(Cart)
            .where(Cart.status != "open")
            .options(
                selectinload(Cart.user),
                selectinload(Cart.items).selectinload(CartItem.product).selectinload(
                    Product.translations
                ),
            )
            .order_by(Cart.created_at.desc())
        )
        .scalars()
        .all()
    )

    enriched_orders = []
    for order in orders:
        total = Decimal("0.00")
        line_items = []
        for item in order.items:
            subtotal = Decimal(item.unit_price or 0) * item.quantity
            total += subtotal
            line_items.append(
                {
                    "id": item.id,
                    "name": _product_display(item.product),
                    "quantity": item.quantity,
                    "unit_price": Decimal(item.unit_price or 0),
                    "subtotal": subtotal,
                }
            )

        enriched_orders.append(
            {
                "order": order,
                "user": getattr(order, "user", None),
                "line_items": line_items,
                "total": total,
            }
        )

    ctx = {
        "orders": enriched_orders,
        "msg": request.query_params.get("msg", ""),
        "err": request.query_params.get("err", ""),
    }

    return templates.TemplateResponse(
        "admin/orders/list.html",
        common_ctx(request, ctx),
    )


@router.post("/admin/orders/{order_id}/status")
async def admin_order_update_status(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    status: str = Form(...),
):
    if not require_admin(request):
        return RedirectResponse("/admin/login?msg=Please%20login", status_code=302)

    allowed = {"pending", "completed", "cancelled"}
    normalized_status = status.strip().lower()
    if normalized_status not in allowed:
        normalized_status = "pending"

    order = db.get(Cart, order_id)
    if not order or order.status == "open":
        return RedirectResponse(
            "/admin/orders?err=Order%20tidak%20ditemukan", status_code=302
        )

    order.status = normalized_status
    db.commit()

    return RedirectResponse(
        "/admin/orders?msg=Status%20diperbarui", status_code=302
    )

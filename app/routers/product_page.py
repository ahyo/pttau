from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.i18n_db import DBI18n
from app.ui import common_ctx, templates

router = APIRouter(tags=["site"])


@router.get("/product", response_class=HTMLResponse)
async def product_page(request: Request, db: Session = Depends(get_db)):
    lang = getattr(request.state, "lang", "id")
    i18n = DBI18n(db, lang)
    return templates.TemplateResponse(
        "site/product.html",
        common_ctx(
            request,
            {
                "lang": lang,
                "i18n": i18n,
            },
        ),
    )

from fastapi import Request
from typing import Optional

LANGS = {"id", "en", "ar"}


def pick_lang(request: Request, default_lang: str = "id") -> str:
    q = request.query_params.get("lang")
    if q in LANGS:
        return q
    cookie = request.cookies.get("lang")
    if cookie in LANGS:
        return cookie
    return default_lang

from sqlalchemy import select
from sqlalchemy.orm import Session


class DBI18n:
    """
    i18n berbasis DB: ambil nilai dari tabel ui_string.
    Gunakan cache per instance (tiap request).
    """

    __slots__ = ("lang", "_cache", "_db")

    def __init__(self, db: Session, lang: str):
        self.lang = lang
        self._cache = {}
        self._db = db

    def t(self, key: str, default: str = "") -> str:
        if key in self._cache:
            return self._cache[key]
        from app.models.ui_string import UIString  # model di bawah

        row = self._db.execute(
            select(UIString.val).where(UIString.k == key, UIString.lang == self.lang)
        ).scalar_one_or_none()
        val = row if row is not None else (default or key)
        self._cache[key] = val
        return val

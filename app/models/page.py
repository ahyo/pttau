from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class Page(Base):
    __tablename__ = "page"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    template = Column(String(50), nullable=False, default="about")
    is_published = Column(Boolean, nullable=False, default=True)
    title = Column(String(255), nullable=False, default="")
    excerpt = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    meta_title = Column(String(255), nullable=True)
    meta_desc = Column(String(255), nullable=True)

    translations = relationship(
        "PageTranslation",
        back_populates="page",
        cascade="all, delete-orphan",
    )

    def get_translation(self, lang: str):
        if not lang or lang == "id":
            return None
        return next((tr for tr in self.translations if tr.lang == lang), None)


class PageTranslation(Base):
    __tablename__ = "page_tr"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("page.id", ondelete="CASCADE"), nullable=False)
    lang = Column(String(5), nullable=False)
    title = Column(String(255), nullable=True)
    excerpt = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    meta_title = Column(String(255), nullable=True)
    meta_desc = Column(String(255), nullable=True)

    page = relationship("Page", back_populates="translations")

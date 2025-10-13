from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
Base = declarative_base()

class Page(Base):
    __tablename__ = "page"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    template = Column(String(50), nullable=False, default="about")
    is_published = Column(Boolean, nullable=False, default=True)
    translations = relationship("PageTR", back_populates="page", cascade="all, delete-orphan")

class PageTR(Base):
    __tablename__ = "page_tr"
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("page.id", ondelete="CASCADE"), nullable=False, index=True)
    lang = Column(String(5), nullable=False)  # id|en|ar
    title = Column(String(255), nullable=False, default="")
    excerpt = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    meta_title = Column(String(255), nullable=True)
    meta_desc = Column(String(255), nullable=True)
    page = relationship("Page", back_populates="translations")
    __table_args__ = (UniqueConstraint("page_id", "lang", name="uix_page_tr_page_lang"),)

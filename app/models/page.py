from sqlalchemy import Column, Integer, String, Boolean, Text
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

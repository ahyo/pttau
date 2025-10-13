from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UIString(Base):
    __tablename__ = "ui_string"
    id = Column(Integer, primary_key=True)
    k = Column(String(100), nullable=False)  # key
    lang = Column(String(5), nullable=False)  # id|en|ar
    val = Column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint("k", "lang", name="uix_ui_string_k_lang"),)

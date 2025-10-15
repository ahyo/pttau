from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class MenuItem(Base):
    __tablename__ = "menu_item"
    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer, ForeignKey("menu_item.id", ondelete="CASCADE"), nullable=True
    )
    position = Column(String(20), nullable=False, default="header")
    url = Column(String(255), nullable=False)
    is_external = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    requires_admin = Column(Boolean, nullable=False, default=False)
    icon = Column(String(64))
    target = Column(String(16))  # _blank / _self

    parent = relationship(
        "MenuItem", remote_side=[id], backref="children", cascade="all, delete"
    )
    translations = relationship(
        "MenuItemTR", back_populates="item", cascade="all, delete-orphan"
    )


class MenuItemTR(Base):
    __tablename__ = "menu_item_tr"
    id = Column(Integer, primary_key=True)
    item_id = Column(
        Integer, ForeignKey("menu_item.id", ondelete="CASCADE"), nullable=False
    )
    lang = Column(String(5), nullable=False)
    label = Column(String(100), nullable=False)

    item = relationship("MenuItem", back_populates="translations")

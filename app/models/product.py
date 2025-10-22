from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    stock = Column(Integer, nullable=False, default=0)
    image_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    translations = relationship(
        "ProductTR", back_populates="product", cascade="all, delete-orphan"
    )
    items = relationship("CartItem", back_populates="product")


class ProductTR(Base):
    __tablename__ = "product_tr"
    __table_args__ = (UniqueConstraint("product_id", "lang", name="uq_product_tr"),)

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="CASCADE"))
    lang = Column(String(5), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    short_description = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    product = relationship("Product", back_populates="translations")

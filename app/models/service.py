from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class Service(Base):
    __tablename__ = "service"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    translations = relationship(
        "ServiceTranslation",
        back_populates="service",
        cascade="all, delete-orphan",
    )

    def get_translation(self, lang: str):
        if not lang or lang == "id":
            return None
        return next((tr for tr in self.translations if tr.lang == lang), None)


class ServiceTranslation(Base):
    __tablename__ = "service_tr"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("service.id", ondelete="CASCADE"), nullable=False)
    lang = Column(String(5), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)

    service = relationship("Service", back_populates="translations")

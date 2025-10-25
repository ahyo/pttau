from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base


class FooterSection(Base):
    __tablename__ = "footer_section"
    id = Column(Integer, primary_key=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    name = Column(String(100), nullable=False)
    links = relationship(
        "FooterLink", back_populates="section", cascade="all, delete-orphan"
    )


class FooterLink(Base):
    __tablename__ = "footer_link"
    id = Column(Integer, primary_key=True)
    section_id = Column(
        Integer,
        ForeignKey("footer_section.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    section = relationship("FooterSection", back_populates="links")
    html_content = Column(Text, nullable=False, default="")

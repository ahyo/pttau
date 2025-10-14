from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db import Base


class FooterSection(Base):
    __tablename__ = "footer_section"
    id = Column(Integer, primary_key=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    translations = relationship(
        "FooterSectionTR", back_populates="section", cascade="all, delete-orphan"
    )
    links = relationship(
        "FooterLink", back_populates="section", cascade="all, delete-orphan"
    )


class FooterSectionTR(Base):
    __tablename__ = "footer_section_tr"
    id = Column(Integer, primary_key=True)
    section_id = Column(
        Integer,
        ForeignKey("footer_section.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lang = Column(String(5), nullable=False)
    name = Column(String(100), nullable=False)
    section = relationship("FooterSection", back_populates="translations")
    __table_args__ = (UniqueConstraint("section_id", "lang", name="uix_section_lang"),)


class FooterLink(Base):
    __tablename__ = "footer_link"
    id = Column(Integer, primary_key=True)
    section_id = Column(
        Integer,
        ForeignKey("footer_section.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(String(255))
    icon = Column(String(50))
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    section = relationship("FooterSection", back_populates="links")
    translations = relationship(
        "FooterLinkTR", back_populates="link", cascade="all, delete-orphan"
    )


class FooterLinkTR(Base):
    __tablename__ = "footer_link_tr"
    id = Column(Integer, primary_key=True)
    link_id = Column(
        Integer,
        ForeignKey("footer_link.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lang = Column(String(5), nullable=False)
    label = Column(String(150), nullable=False)
    link = relationship("FooterLink", back_populates="translations")
    __table_args__ = (UniqueConstraint("link_id", "lang", name="uix_link_lang"),)

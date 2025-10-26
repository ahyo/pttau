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
    translations = relationship(
        "FooterSectionTranslation",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def get_translation(self, lang: str):
        if not lang or lang == "id":
            return None
        return next((tr for tr in self.translations if tr.lang == lang), None)


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

    translations = relationship(
        "FooterLinkTranslation",
        back_populates="link",
        cascade="all, delete-orphan",
    )

    def get_translation(self, lang: str):
        if not lang or lang == "id":
            return None
        return next((tr for tr in self.translations if tr.lang == lang), None)


class FooterSectionTranslation(Base):
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


class FooterLinkTranslation(Base):
    __tablename__ = "footer_link_tr"

    id = Column(Integer, primary_key=True)
    link_id = Column(
        Integer,
        ForeignKey("footer_link.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lang = Column(String(5), nullable=False)
    html_content = Column(Text, nullable=False, default="")

    link = relationship("FooterLink", back_populates="translations")

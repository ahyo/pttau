from sqlalchemy import Column, Integer, String, Boolean, Text
from app.db import Base


class CarouselItem(Base):
    __tablename__ = "carousel_item"
    id = Column(Integer, primary_key=True)
    media_type = Column(String(10), nullable=False, default="image")  # image|video
    media_path = Column(
        String(255), nullable=False
    )  # /static/img/.. atau /static/video/..
    poster_path = Column(String(255), nullable=True)  # poster utk video (optional)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=True)
    subtitle = Column(Text, nullable=True)
    cta_text = Column(String(100), nullable=True)
    cta_url = Column(String(255), nullable=True)

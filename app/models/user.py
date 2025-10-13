from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

# Jika kamu sudah punya Base di models/base.py, impor itu saja.
# Di sini untuk mandiri:
Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=True)

from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Firmatario(Base):
    __tablename__ = "firmatari"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, index=True, nullable=False)

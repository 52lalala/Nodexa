from sqlalchemy import Column, String, Float
from sqlalchemy.dialects.postgresql import JSONB
from db.connection import Base


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    attributes = Column(JSONB, default=dict)

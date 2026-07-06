from sqlalchemy import Column, String, Float, BigInteger
from db.connection import Base


class Relation(Base):
    __tablename__ = "relations"

    id = Column(String, primary_key=True)
    from_node = Column(String, nullable=False)
    to_node = Column(String, nullable=False)
    type = Column(String, nullable=False)
    weight = Column(Float, default=0.0)
    timestamp = Column(BigInteger, default=0)

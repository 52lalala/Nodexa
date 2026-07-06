from sqlalchemy import Column, String, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from db.connection import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    context = Column(JSONB, default=dict)
    timestamp = Column(BigInteger, default=0)

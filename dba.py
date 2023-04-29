import logging
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from django.conf import settings

# local imports
from .dateutils import local_now_tz_aware

Base = declarative_base()


class LogEntry(Base):
    __tablename__ = 'helpers_logentry'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False, default=logging.ERROR)
    msg = Column(Text, nullable=False)
    trace = Column(Text, nullable=False)
    task_id = Column(String(12), nullable=False)
    username = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), default=local_now_tz_aware())

    def __str__(self):
        return self.msg


engine = create_engine(settings.SQLALCHEMY_DB_CONNECTION)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

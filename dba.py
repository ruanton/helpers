"""
Access to Django project database objects via SqlAlchemy.
Exposes: Session factory object and Mirror for some Django objects.
"""

import datetime
import logging
from sqlalchemy import create_engine, DateTime, Integer, String, Text, BigInteger
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from django.conf import settings

# local imports
from .dateutils import local_now_tz_aware
from .models import LogEntry as DjangoOrmLogEntry


class Base(DeclarativeBase):
    pass


class LogEntry(Base):
    __tablename__ = DjangoOrmLogEntry._meta.db_table

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=logging.ERROR)
    msg: Mapped[str] = mapped_column(Text, nullable=False)
    trace: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str] = mapped_column(String(12), nullable=False)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=local_now_tz_aware()
    )

    def __repr__(self):
        return f'{self.created_at:%Y%m%d-%H%M%S.%f}: {self.msg}'


def derive_sa_connection_string() -> str:
    """
    Derives SqlAlchemy database connection string from Django default database configuration.
    """
    db_settings = settings.DATABASES['default']

    if db_settings['ENGINE'] == 'django.db.backends.sqlite3':
        sql_alchemy_connection = f'sqlite:///{db_settings["NAME"]}'

    elif db_settings['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
        user = db_settings['USER']
        password = db_settings['PASSWORD']
        host = db_settings['HOST'] if 'HOST' in db_settings else 'localhost'
        port = f':{db_settings["PORT"]}' if 'PORT' in db_settings else ''
        name = db_settings['NAME']
        sql_alchemy_connection = f'postgresql+psycopg2://{user}:{password}@{host}{port}/{name}'

    else:
        # to extend: https://docs.sqlalchemy.org/en/20/core/engines.html
        raise ValueError(f'cannot derive SqlAlchemy connection string from settings.DATABASE')

    return sql_alchemy_connection


engine = create_engine(derive_sa_connection_string())
"""Default database engine."""

Session = sessionmaker(bind=engine)
"""
SqlAlchemy Session objects creator, bound to configured database connection.

Can use shortcut "with Session.begin() as session:" equivalent to "with Session() as session, session.begin():".
This creates/closes Session object and begins/commits transaction.
"""

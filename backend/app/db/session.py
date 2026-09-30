from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url

from app.core.config import settings


engine_options: dict = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

if settings.database_url == "sqlite://":
    engine_options["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_options)

if settings.database_url.startswith("sqlite"):
    sqlite_database = make_url(settings.database_url).database
    if sqlite_database in (None, "", ":memory:"):
        public_database = ":memory:"
    else:
        database_path = Path(sqlite_database)
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path
        public_database = str(
            database_path.with_name(database_path.stem + "_public" + database_path.suffix)
        )

    @event.listens_for(engine, "connect")
    def attach_public_schema(dbapi_connection, connection_record) -> None:
        attached = {
            row[1]
            for row in dbapi_connection.execute("PRAGMA database_list").fetchall()
        }
        if "public" not in attached:
            dbapi_connection.execute(
                'ATTACH DATABASE ? AS "public"',
                (public_database,),
            )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

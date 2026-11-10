"""UC3M MariaDB configuration without connecting to the restricted lab server."""

from app import create_app
from models import db
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable


def test_database_uri_from_environment(monkeypatch):
    # The app can initialize its engine without contacting the lab's MariaDB server.
    uri = "mysql+pymysql://27_webapp_42:example@mysql.lab.it.uc3m.es/27_webapp_42a"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", uri)
    app = create_app()
    assert app.config["SQLALCHEMY_DATABASE_URI"] == uri
    with app.app_context():
        assert db.engine.url.drivername == "mysql+pymysql"
        assert db.engine.url.database == "27_webapp_42a"


def test_mysql_ddl_compiles_without_connection():
    # Ensure each existing model remains representable as MariaDB/MySQL DDL.
    tables = db.metadata.sorted_tables
    assert tables
    for table in tables:
        sql = str(CreateTable(table).compile(dialect=mysql.dialect()))
        assert "CREATE TABLE" in sql

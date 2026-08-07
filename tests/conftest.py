import pytest

import cardarb.db.database as database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Points the DB connection at a throwaway SQLite file for the duration of the test."""
    db_path = tmp_path / "test_arbitrage.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    yield db_path

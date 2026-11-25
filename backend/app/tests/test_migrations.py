from pathlib import Path

from alembic.config import Config

from alembic import command


def test_alembic_upgrade_head_on_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    # Clear settings cache so alembic env picks up test DATABASE_URL.
    from app.core.config import get_settings

    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(backend_dir)

    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")

    command.upgrade(config, "head")

    assert db_path.exists()
    get_settings.cache_clear()

import sqlite3
import uuid
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


def test_role_migration_preserves_existing_user_roles(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from app.core.config import get_settings

    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(backend_dir)
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")

    command.upgrade(config, "0001_initial_identity")

    company_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    super_admin_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO companies (id, legal_name, status) VALUES (?, ?, ?)",
            (company_id, "Migration Test SpA", "active"),
        )
        for user_id, email, role, user_company_id in [
            (admin_id, "admin@example.com", "admin", company_id),
            (super_admin_id, "platform@example.com", "super_admin", None),
        ]:
            connection.execute(
                """
                INSERT INTO users (
                    id, company_id, email, first_name, last_name, password_hash,
                    role, status, must_change_password, failed_login_attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_company_id,
                    email,
                    "Test",
                    "User",
                    "preserved-password-hash",
                    role,
                    "active",
                    0,
                    0,
                ),
            )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(db_path) as connection:
        migrated_users = dict(
            connection.execute(
                """
                SELECT users.email, roles.code
                FROM users
                JOIN roles ON roles.id = users.role_id
                """
            ).fetchall()
        )
        migrated_scopes = dict(
            connection.execute("SELECT email, role_scope FROM users").fetchall()
        )
        preserved = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("admin@example.com",),
        ).fetchone()
        permission_count = connection.execute(
            "SELECT COUNT(*) FROM permissions"
        ).fetchone()[0]

    assert migrated_users == {
        "admin@example.com": "admin",
        "platform@example.com": "super_admin",
    }
    assert migrated_scopes == {
        "admin@example.com": "company",
        "platform@example.com": "platform",
    }
    assert preserved == ("preserved-password-hash",)
    assert permission_count == 36

    command.downgrade(config, "0001_initial_identity")

    with sqlite3.connect(db_path) as connection:
        restored_roles = dict(connection.execute("SELECT email, role FROM users").fetchall())
        restored_hash = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("admin@example.com",),
        ).fetchone()

    assert restored_roles == {
        "admin@example.com": "admin",
        "platform@example.com": "super_admin",
    }
    assert restored_hash == ("preserved-password-hash",)
    get_settings.cache_clear()

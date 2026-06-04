from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_config_files_exist():
    assert (BACKEND_ROOT / "alembic.ini").exists()
    assert (BACKEND_ROOT / "alembic" / "env.py").exists()
    assert (BACKEND_ROOT / "alembic" / "versions").is_dir()


def test_alembic_env_includes_schemas():
    env_text = (BACKEND_ROOT / "alembic" / "env.py").read_text()

    assert "include_schemas=True" in env_text
    assert "target_metadata = Base.metadata" in env_text


def test_runtime_create_all_removed_from_main():
    main_text = (BACKEND_ROOT / "main.py").read_text()

    assert "Base.metadata.create_all" not in main_text


def test_legacy_migrate_script_no_longer_creates_schema():
    migrate_text = (BACKEND_ROOT / "ops" / "migrate_db.py").read_text()

    assert "Base.metadata.create_all" not in migrate_text
    assert "alembic" in migrate_text.lower()

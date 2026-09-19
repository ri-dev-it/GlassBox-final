import datetime
import json
import os
import shutil
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, func, select, update


def _database_url() -> str:
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return configured
    backend_db = Path(__file__).resolve().parents[2] / "backend" / "xai_loan.db"
    return f"sqlite:///{backend_db.as_posix()}"


def _table(metadata: MetaData) -> Table:
    return Table(
        "model_versions", metadata,
        Column("id", Integer, primary_key=True),
        Column("model_name", String(50), nullable=False),
        Column("version_number", Integer, nullable=False),
        Column("trained_at", DateTime, nullable=False),
        Column("file_path", String(512), nullable=False),
        Column("metrics_json", Text, nullable=False),
        Column("governance_passed", Boolean, nullable=False),
        Column("is_active", Boolean, nullable=False),
    )


def register_model_version(model_name: str, source_path: str, metadata: dict) -> dict:
    """Copy an artifact into the durable versions directory and register it.

    This uses the configured application database, creating the table for a
    fresh local training checkout. Existing active versions remain active when
    governance rejects the newly trained artifact.
    """
    source = Path(source_path).resolve()
    versions_dir = source.parent / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(_database_url())
    metadata_obj = MetaData()
    versions = _table(metadata_obj)
    metadata_obj.create_all(engine, tables=[versions], checkfirst=True)
    governance = metadata.get("governance", {})
    passed = bool(governance.get("passed", False))
    with engine.begin() as connection:
        latest = connection.execute(select(func.max(versions.c.version_number)).where(versions.c.model_name == model_name)).scalar() or 0
        version_number = int(latest) + 1
        destination = versions_dir / f"{model_name}_v{version_number}{source.suffix}"
        shutil.copy2(source, destination)
        if passed:
            connection.execute(update(versions).where(versions.c.model_name == model_name).values(is_active=False))
        result = connection.execute(versions.insert().values(
            model_name=model_name,
            version_number=version_number,
            trained_at=datetime.datetime.utcnow(),
            file_path=str(destination),
            metrics_json=json.dumps({key: metadata.get(key) for key in ("precision", "recall", "f1", "roc_auc")}),
            governance_passed=passed,
            is_active=passed,
        ))
        version_id = result.inserted_primary_key[0]
    return {"id": version_id, "version_number": version_number, "file_path": str(destination), "governance_passed": passed, "is_active": passed}
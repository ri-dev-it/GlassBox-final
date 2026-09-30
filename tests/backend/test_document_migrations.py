from pathlib import Path
from flask_migrate import stamp, upgrade, downgrade
from sqlalchemy import inspect
from app.extensions import db


def test_document_migrations_round_trip(app):
    directory = str(Path(__file__).parents[2] / 'backend/migrations')
    tables = ['document_fingerprints', 'document_transactions', 'verification_reports', 'document_audits']
    with app.app_context():
        for name in tables:
            db.metadata.tables[name].drop(db.engine)
        stamp(directory=directory, revision='l820260927')
        upgrade(directory=directory)
        assert set(tables) <= set(inspect(db.engine).get_table_names())
        downgrade(directory=directory, revision='l820260927')
        assert not set(tables) & set(inspect(db.engine).get_table_names())
        upgrade(directory=directory)
        assert set(tables) <= set(inspect(db.engine).get_table_names())

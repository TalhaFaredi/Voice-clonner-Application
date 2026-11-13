import sqlite3
from contextlib import contextmanager
from pathlib import Path
from flask import current_app

SCHEMA_DIR = Path(__file__).resolve().parents[3] / 'database' / 'migrations'


def connect():
    db = sqlite3.connect(current_app.config['DATABASE'], timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=30000')
    return db


@contextmanager
def transaction():
    db = connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def rows(sql, args=(), one=False):
    db = connect()
    try:
        data = db.execute(sql, args).fetchall()
        return (dict(data[0]) if data else None) if one else [dict(r) for r in data]
    finally:
        db.close()


def init_database(app):
    Path(app.config['STORAGE']).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db = connect()
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)')
            db.execute('BEGIN IMMEDIATE')
            for path in sorted(SCHEMA_DIR.glob('*.sql')):
                if not db.execute('SELECT 1 FROM migrations WHERE name=?', (path.name,)).fetchone():
                    statement=''
                    for line in path.read_text(encoding='utf-8').splitlines(keepends=True):
                        statement+=line
                        if sqlite3.complete_statement(statement):
                            db.execute(statement)
                            statement=''
                    if statement.strip():
                        raise ValueError(f'Incomplete SQL migration: {path.name}')
                    db.execute('INSERT INTO migrations VALUES(?)',(path.name,))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

"""Consistent backup of the SQLite database and private audio.

Usage: python scripts/backup.py [destination_dir] [--keep N]

Uses SQLite's online backup API, so it is safe while the API and worker run
(unlike copying a WAL-mode database file). Writes one timestamped folder
containing saas.sqlite3 plus a copy of storage/users. Backups contain private
user audio: store them encrypted and access-restricted.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

STORAGE = Path(__file__).resolve().parents[1] / 'backend' / 'storage'


def backup(destination, keep=14, storage=STORAGE):
    database = storage / 'saas.sqlite3'
    if not database.exists():
        raise SystemExit(f'No database at {database}')
    destination = Path(destination)
    target = destination / datetime.now().strftime('backup-%Y%m%d-%H%M%S-%f')
    target.mkdir(parents=True)
    source = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
    copy = sqlite3.connect(target / 'saas.sqlite3')
    try:
        source.backup(copy)
        if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup failed integrity check; it was not kept.')
    finally:
        copy.close()
        source.close()
    users = storage / 'users'
    if users.exists():
        shutil.copytree(users, target / 'users')
    old = sorted(p for p in destination.glob('backup-*') if p.is_dir())
    for stale in old[:-keep] if keep > 0 else []:
        shutil.rmtree(stale)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', nargs='?', default=str(STORAGE.parent / 'backups'))
    parser.add_argument('--keep', type=int, default=14)
    args = parser.parse_args()
    print(f'Backup written to {backup(args.destination, args.keep)}')

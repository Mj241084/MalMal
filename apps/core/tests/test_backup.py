import os
import sqlite3
from contextlib import closing

import pytest
from django.core.management import call_command


@pytest.mark.django_db(transaction=True)
def test_backup_is_verified_and_old_copies_are_dropped(settings, tmp_path, buyer):
    settings.BACKUP_DIR = str(tmp_path)
    old = tmp_path / "db-20200101-000000.sqlite3"
    old.write_bytes(b"x")
    os.utime(old, (0, 0))

    call_command("backup_db", verbosity=0)

    copies = list(tmp_path.glob("db-*.sqlite3"))
    assert len(copies) == 1 and not old.exists()
    with closing(sqlite3.connect(copies[0])) as db:
        assert db.execute("SELECT COUNT(*) FROM accounts_user").fetchone()[0] == 1

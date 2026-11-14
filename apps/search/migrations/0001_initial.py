"""Initial FTS5 index for product search (docs/03 §7).

The virtual table is created with RunSQL because Django's ORM cannot model FTS5.
It is a regular (not contentless) FTS5 table so DELETE/INSERT work on every
SQLite build; the catalog is small and the duplicated text is cheap.
"""

from __future__ import annotations

from django.db import migrations

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS product_fts USING fts5(
  product_id UNINDEXED,
  title,
  brand,
  category,
  model_codes,
  tokens,
  tokenize='unicode61 remove_diacritics 2',
  prefix='2 3 4'
);
"""

DROP_FTS = "DROP TABLE IF EXISTS product_fts;"


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_FTS, reverse_sql=DROP_FTS),
    ]

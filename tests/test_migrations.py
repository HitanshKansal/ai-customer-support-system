"""Tests for migration ordering and current schema head."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_migration_chain_has_expected_head() -> None:
    config = Config("alembic.ini")
    scripts = ScriptDirectory.from_config(config)
    revisions = list(scripts.walk_revisions())

    assert revisions[0].revision == "20260926_0005"
    assert revisions[0].down_revision == "20260926_0004"
    assert revisions[-1].revision == "20260926_0001"
    assert revisions[-1].down_revision is None

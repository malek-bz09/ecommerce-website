"""The migrations and the models must describe the same tables."""

from alembic import command

from tests.conftest import alembic_config


def test_models_match_migrations():
    # Fails if a model was changed without creating a migration for it
    command.check(alembic_config())


def test_migrations_can_be_undone_and_redone():
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")

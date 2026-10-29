"""Initial empty revision: the starting point later migrations build on.

Creates no tables. Running it adds Alembic's own "alembic_version" table,
which records which migration the database is at.

Revision ID: 4a5de4bed307
Revises: 
Create Date: 2026-10-17 18:19:31.642099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a5de4bed307'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

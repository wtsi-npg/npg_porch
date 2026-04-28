"""remove_obsolete_pipeline_links

Revision ID: 3.0.0a
Revises: 3.0.0
Create Date: 2026-02-26 15:02:11.786337

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3.0.0a"
down_revision: Union[str, Sequence[str], None] = "3.0.0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    sql = """
    ALTER TABLE npg_porch.pipeline DROP COLUMN version
    """
    op.execute(sql)
    sql = """
    ALTER TABLE npg_porch.task DROP COLUMN pipeline_id
    """
    op.execute(sql)


# No downgrade function as the creation for multiple versions prevents unique
# pipelines from being recreated.  This will cause an error on attempting to downgrade.

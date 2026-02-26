"""add_version_table

Revision ID: 3.0.0
Revises: bb1c7a5b3a1a
Create Date: 2026-02-26 14:40:08.058286

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3.0.0"
down_revision: Union[str, Sequence[str], None] = "bb1c7a5b3a1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    sql = """
    CREATE TABLE npg_porch.version (
    version_id SERIAL PRIMARY KEY,
    version VARCHAR(32) NOT NULL,
    pipeline_id INT NOT NULL REFERENCES npg_porch.pipeline (pipeline_id),
    CONSTRAINT unique_version UNIQUE(version, pipeline_id)
    )
    """
    op.execute(sql)
    sql = """
    INSERT INTO npg_porch.version (version, pipeline_id) SELECT version, pipeline_id FROM npg_porch.pipeline
    """
    op.execute(sql)
    sql = """
    ALTER TABLE npg_porch.task 
    ADD COLUMN version_id INT,
    DROP CONSTRAINT unique_tasks,
    ADD CONSTRAINT task_version_id_fkey FOREIGN KEY (version_id) REFERENCES npg_porch.version (version_id),
    ADD CONSTRAINT unique_tasks UNIQUE (version_id, job_descriptor)
    """
    op.execute(sql)
    sql = """
    UPDATE npg_porch.task AS t SET version_id = v.version_id FROM 
    npg_porch.version AS v JOIN npg_porch.pipeline AS p USING (pipeline_id) 
    WHERE p.pipeline_id = t.pipeline_id
    """
    op.execute(sql)
    sql = """
    GRANT SELECT ON TABLE npg_porch.version TO npg_ro
    """
    op.execute(sql)
    sql = """
    GRANT INSERT, DELETE, SELECT, UPDATE ON TABLE npg_porch.version TO npg_rw
    """
    op.execute(sql)


def downgrade() -> None:
    """Downgrade schema."""
    sql = """
    ALTER TABLE npg_porch.task
    DROP CONSTRAINT unique_tasks,
    ADD CONSTRAINT unique_tasks UNIQUE (pipeline_id, job_descriptor)
    DROP COLUMN version_id;
    """
    op.execute(sql)
    sql = """
    DROP TABLE npg_porch.version;
    """
    op.execute(sql)

"""squashed baseline wazo-23.05

Revision ID: d6a8d09c2f29
Revises: None

"""

import os

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd6a8d09c2f29'
down_revision = None


def upgrade():
    # Read and execute the SQL dump file
    versions_dir_path = os.path.dirname(__file__)
    sql_file_path = os.path.join(versions_dir_path, 'baseline-2305.sql')

    with open(sql_file_path) as f:
        sql_content = f.read()

    # Execute the SQL content
    op.execute(sql_content)


def downgrade():
    pass

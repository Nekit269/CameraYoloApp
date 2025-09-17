"""create posts table

Revision ID: 1dde742c5c9c
Revises: 
Create Date: 2025-09-16 15:25:57.785067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dde742c5c9c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE posts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            body VARCHAR(200)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE posts")

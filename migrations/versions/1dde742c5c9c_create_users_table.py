"""create users table

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
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50),
            password TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE users")

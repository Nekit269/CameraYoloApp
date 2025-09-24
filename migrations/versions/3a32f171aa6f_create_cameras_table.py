"""create_cameras_table

Revision ID: 3a32f171aa6f
Revises: 1dde742c5c9c
Create Date: 2025-09-23 15:16:02.654012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a32f171aa6f'
down_revision: Union[str, Sequence[str], None] = '1dde742c5c9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE cameras (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            url VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE cameras")

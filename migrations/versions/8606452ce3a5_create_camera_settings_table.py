"""create_camera_settings_table

Revision ID: 8606452ce3a5
Revises: 3a32f171aa6f
Create Date: 2025-09-25 09:40:47.322152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8606452ce3a5'
down_revision: Union[str, Sequence[str], None] = '3a32f171aa6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE cameras_settings (
            id SERIAL PRIMARY KEY,
            camera_id INTEGER REFERENCES cameras(id) ON DELETE CASCADE,
            model_name VARCHAR(50) DEFAULT 'yolov8n',
            confidence_threshold INTEGER DEFAULT 30
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE cameras_settings")

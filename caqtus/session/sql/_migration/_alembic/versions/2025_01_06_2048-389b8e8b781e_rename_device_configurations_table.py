"""Rename device configurations table

Revision ID: 389b8e8b781e
Revises: 22d4b5bd16cb
Create Date: 2025-01-06 20:48:37.745921

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "389b8e8b781e"
down_revision: Union[str, None] = "22d4b5bd16cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("sequence.device_configurations", "device_config")
    op.execute(
        'ALTER SEQUENCE "sequence.device_configurations_id__seq" RENAME TO device_config_id_seq'
    )


def downgrade() -> None:
    op.rename_table("device_config", "sequence.device_configurations")
    op.execute(
        'ALTER SEQUENCE device_config_id_seq RENAME TO "sequence.device_configurations_id__seq"'
    )

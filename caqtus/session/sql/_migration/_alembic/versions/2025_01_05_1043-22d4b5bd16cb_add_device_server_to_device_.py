"""Add device server to device configurations tables

Revision ID: 22d4b5bd16cb
Revises: babf96303363
Create Date: 2025-01-05 10:43:09.051222

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "22d4b5bd16cb"
down_revision: Union[str, None] = "babf96303363"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "default_device_configurations",
        sa.Column("device_server", sa.String(), nullable=True),
    )
    op.add_column(
        "sequence.device_configurations",
        sa.Column("device_server", sa.String(), nullable=True),
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported")
    # op.drop_column('sequence.device_configurations', 'device_server')
    # op.drop_column('default_device_configurations', 'device_server')

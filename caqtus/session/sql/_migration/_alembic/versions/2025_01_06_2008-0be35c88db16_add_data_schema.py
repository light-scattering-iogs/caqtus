"""Add data schema

Revision ID: 0be35c88db16
Revises: 22d4b5bd16cb
Create Date: 2025-01-06 20:08:33.323044

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0be35c88db16"
down_revision: Union[str, None] = "22d4b5bd16cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sequence.data_schema",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_configuration_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("data_type", sa.JSON(), nullable=False),
        sa.Column("retention_policy", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_configuration_id"],
            ["sequence.device_configurations.id_"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_configuration_id", "label"),
    )
    op.create_index(
        op.f("ix_sequence.data_schema_device_configuration_id"),
        "sequence.data_schema",
        ["device_configuration_id"],
        unique=False,
    )
    op.create_table(
        "shot.data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shot_id", sa.Integer(), nullable=False),
        sa.Column("schema_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["schema_id"], ["sequence.data_schema.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shot_id", "schema_id"),
    )
    op.create_index(
        op.f("ix_shot.data_schema_id"), "shot.data", ["schema_id"], unique=False
    )
    op.create_index(
        op.f("ix_shot.data_shot_id"), "shot.data", ["shot_id"], unique=False
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported.")
    # op.drop_index(op.f('ix_shot.data_shot_id'), table_name='shot.data')
    # op.drop_index(op.f('ix_shot.data_schema_id'), table_name='shot.data')
    # op.drop_table('shot.data')
    # op.drop_index(op.f('ix_sequence.data_schema_device_configuration_id'), table_name='sequence.data_schema')
    # op.drop_table('sequence.data_schema')

"""Add parameter schema

Revision ID: b94f95eeee73
Revises: dca55c13283b
Create Date: 2025-01-07 19:31:47.812439

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b94f95eeee73"
down_revision: Union[str, None] = "dca55c13283b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parameter_schema",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("parameter_name", sa.String(), nullable=False),
        sa.Column("parameter_type", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sequence_id"], ["sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id", "parameter_name"),
    )
    op.create_index(
        op.f("ix_parameter_schema_sequence_id"),
        "parameter_schema",
        ["sequence_id"],
        unique=False,
    )
    op.create_table(
        "shot_parameter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shot_id", sa.Integer(), nullable=False),
        sa.Column("parameter_schema_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parameter_schema_id"], ["parameter_schema.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shot_id", "parameter_schema_id"),
    )
    op.create_index(
        op.f("ix_shot_parameter_parameter_schema_id"),
        "shot_parameter",
        ["parameter_schema_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shot_parameter_shot_id"), "shot_parameter", ["shot_id"], unique=False
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported")
    # op.drop_index(op.f('ix_shot_parameter_shot_id'), table_name='shot_parameter')
    # op.drop_index(op.f('ix_shot_parameter_parameter_schema_id'), table_name='shot_parameter')
    # op.drop_table('shot_parameter')
    # op.drop_index(op.f('ix_parameter_schema_sequence_id'), table_name='parameter_schema')
    # op.drop_table('parameter_schema')

"""empty message

Revision ID: 1e67b085fe68
Revises: 038164d73465
Create Date: 2024-08-24 11:23:25.088629

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1e67b085fe68"
down_revision: Union[str, None] = "038164d73465"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sequence.exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column(
            "type", sa.Enum("SYSTEM", "USER", name="exceptiontype"), nullable=False
        ),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["sequence_id"], ["sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id", "type", name="exception"),
    )
    op.create_index(
        op.f("ix_sequence.exceptions_sequence_id"),
        "sequence.exceptions",
        ["sequence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_sequence.exceptions_sequence_id"), table_name="sequence.exceptions"
    )
    op.drop_table("sequence.exceptions")

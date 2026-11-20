"""scheduled runs unique per day

Revision ID: 7b25d3c8f22c
Revises: 266b293dab58
Create Date: 2026-11-20 17:52:20.283543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b25d3c8f22c'
down_revision: Union[str, Sequence[str], None] = '266b293dab58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Only scheduled runs are unique per kind and day; manual runs may repeat."""
    op.drop_index("uq_model_runs_success_per_day", table_name="model_runs")
    op.create_index(
        "uq_model_runs_success_per_day", "model_runs", ["kind", "run_date"], unique=True,
        postgresql_where=sa.text("status = 'success' AND triggered_by = 'scheduler'"),
    )


def downgrade() -> None:
    op.drop_index("uq_model_runs_success_per_day", table_name="model_runs")
    op.create_index(
        "uq_model_runs_success_per_day", "model_runs", ["kind", "run_date"], unique=True,
        postgresql_where=sa.text("status = 'success'"),
    )

"""add hourly_rates, surcharges and wait_time_rules tables

Revision ID: e170e6bb437b
Revises: 0dd907862d09
Create Date: 2026-07-29 16:46:46.996079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e170e6bb437b'
down_revision: Union[str, Sequence[str], None] = '0dd907862d09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE : rempli à la main - autogenerate a vu ces tables déjà présentes
    # sur la base de dev (créées par Base.metadata.create_all via le
    # rechargement d'uvicorn --reload après l'édition de models.py) et a
    # donc généré un upgrade() vide. Ce contenu reproduit exactement les
    # modèles HourlyRate / Surcharge / WaitTimeRule pour qu'une base
    # neuve obtienne bien ces tables.
    op.create_table('hourly_rates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vehicle_code', sa.String(), nullable=False),
    sa.Column('hourly_rate', sa.Float(), nullable=False),
    sa.Column('minimum_hours', sa.Integer(), nullable=False),
    sa.Column('notice_hours', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hourly_rates_id'), 'hourly_rates', ['id'], unique=False)
    op.create_index(op.f('ix_hourly_rates_vehicle_code'), 'hourly_rates', ['vehicle_code'], unique=True)
    op.create_table('surcharges',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=True),
    sa.Column('percent', sa.Float(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_surcharges_code'), 'surcharges', ['code'], unique=True)
    op.create_index(op.f('ix_surcharges_id'), 'surcharges', ['id'], unique=False)
    op.create_table('wait_time_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('trip_type', sa.String(), nullable=False),
    sa.Column('grace_period_minutes', sa.Integer(), nullable=False),
    sa.Column('increment_minutes', sa.Integer(), nullable=False),
    sa.Column('rate_per_increment', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wait_time_rules_id'), 'wait_time_rules', ['id'], unique=False)
    op.create_index(op.f('ix_wait_time_rules_trip_type'), 'wait_time_rules', ['trip_type'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_wait_time_rules_trip_type'), table_name='wait_time_rules')
    op.drop_index(op.f('ix_wait_time_rules_id'), table_name='wait_time_rules')
    op.drop_table('wait_time_rules')
    op.drop_index(op.f('ix_surcharges_id'), table_name='surcharges')
    op.drop_index(op.f('ix_surcharges_code'), table_name='surcharges')
    op.drop_table('surcharges')
    op.drop_index(op.f('ix_hourly_rates_vehicle_code'), table_name='hourly_rates')
    op.drop_index(op.f('ix_hourly_rates_id'), table_name='hourly_rates')
    op.drop_table('hourly_rates')

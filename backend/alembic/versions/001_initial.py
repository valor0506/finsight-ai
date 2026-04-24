"""create initial tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id',              sa.String(),     primary_key=True),
        sa.Column('email',           sa.String(255),  nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(),     nullable=False),
        sa.Column('full_name',       sa.String(255),  nullable=True),
        sa.Column('tier',            sa.String(50),   server_default='free'),
        sa.Column('is_active',       sa.Boolean(),    server_default='true'),
        sa.Column('created_at',      sa.DateTime(),   server_default=sa.func.now()),
    )

    op.create_table(
        'reports',
        sa.Column('id',              sa.String(),     primary_key=True),
        sa.Column('user_id',         sa.String(),     sa.ForeignKey('users.id'), nullable=False),
        sa.Column('asset_type',      sa.String(50)),
        sa.Column('asset_symbol',    sa.String(50)),
        sa.Column('analysis_type',   sa.String(50)),
        sa.Column('status',          sa.String(50),   server_default='pending'),
        sa.Column('celery_task_id',  sa.String(),     nullable=True),
        sa.Column('error_message',   sa.Text(),       nullable=True),
        sa.Column('file_url',        sa.String(),     nullable=True),
        sa.Column('file_size_kb',    sa.Integer(),    nullable=True),
        sa.Column('report_metadata', sa.JSON(),       server_default='{}'),
        sa.Column('created_at',      sa.DateTime(),   server_default=sa.func.now()),
        sa.Column('completed_at',    sa.DateTime(),   nullable=True),
    )

    op.create_table(
        'watchlists',
        sa.Column('id',           sa.String(),    primary_key=True),
        sa.Column('user_id',      sa.String(),    sa.ForeignKey('users.id'), nullable=False),
        sa.Column('asset_symbol', sa.String(50),  nullable=False),
        sa.Column('asset_type',   sa.String(50),  nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('created_at',   sa.DateTime(),  server_default=sa.func.now()),
    )

    op.create_table(
        'cached_data',
        sa.Column('id',          sa.String(),    primary_key=True),
        sa.Column('cache_key',   sa.String(255), unique=True, nullable=False),
        sa.Column('data',        sa.JSON(),      nullable=False),
        sa.Column('fetched_at',  sa.DateTime(),  server_default=sa.func.now()),
        sa.Column('ttl_minutes', sa.Integer(),   server_default='15'),
    )

    op.create_index('ix_reports_user_id',    'reports',    ['user_id'])
    op.create_index('ix_reports_created_at', 'reports',    ['created_at'])
    op.create_index('ix_watchlists_user_id', 'watchlists', ['user_id'])


def downgrade() -> None:
    op.drop_table('cached_data')
    op.drop_table('watchlists')
    op.drop_table('reports')
    op.drop_table('users')
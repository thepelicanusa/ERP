"""create all tables from SQLAlchemy metadata (dev-friendly)

Revision ID: 0004_create_all_tables
Revises: 0003_email_engine_prefix
Create Date: 2026-02-01T22:33:53.269472Z
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_create_all_tables"
down_revision = "0003_email_engine_prefix"
branch_labels = None
depends_on = None

def upgrade():
    # NOTE: This build previously relied on Base.metadata.create_all() at runtime.
    # This migration makes schema creation reproducible for environments that require migrations.
    from app.db.base import Base  # imported here so Alembic env can load models
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade():
    from app.db.base import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

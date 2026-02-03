"""baseline

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-02-01T20:37:33.847846Z
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Baseline migration.
    # In production, regenerate with: alembic revision --autogenerate -m "init"
    pass

def downgrade():
    pass

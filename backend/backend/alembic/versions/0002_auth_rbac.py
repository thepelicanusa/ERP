"""auth rbac

Revision ID: 0002_auth_rbac
Revises: 0001_baseline
Create Date: 2026-02-01T21:30:00Z
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth_rbac"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_user",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("full_name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_auth_user_email", "auth_user", ["email"], unique=True)

    op.create_table(
        "auth_role",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False, server_default=""),
    )
    op.create_index("ix_auth_role_name", "auth_role", ["name"], unique=True)

    op.create_table(
        "auth_permission",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False, server_default=""),
    )
    op.create_index("ix_auth_permission_code", "auth_permission", ["code"], unique=True)

    op.create_table(
        "auth_user_role",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_user.id"), nullable=False),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("auth_role.id"), nullable=False),
    )
    op.create_index("uq_auth_user_role_user_role", "auth_user_role", ["user_id", "role_id"], unique=True)

    op.create_table(
        "auth_role_permission",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("auth_role.id"), nullable=False),
        sa.Column("permission_id", sa.String(length=36), sa.ForeignKey("auth_permission.id"), nullable=False),
    )
    op.create_index("uq_auth_role_perm_role_perm", "auth_role_permission", ["role_id", "permission_id"], unique=True)


def downgrade():
    op.drop_index("uq_auth_role_perm_role_perm", table_name="auth_role_permission")
    op.drop_table("auth_role_permission")
    op.drop_index("uq_auth_user_role_user_role", table_name="auth_user_role")
    op.drop_table("auth_user_role")
    op.drop_index("ix_auth_permission_code", table_name="auth_permission")
    op.drop_table("auth_permission")
    op.drop_index("ix_auth_role_name", table_name="auth_role")
    op.drop_table("auth_role")
    op.drop_index("ix_auth_user_email", table_name="auth_user")
    op.drop_table("auth_user")

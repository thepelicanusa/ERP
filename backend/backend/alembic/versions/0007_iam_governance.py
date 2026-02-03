"""IAM governance: scoped RBAC grants, refresh tokens, audit context.

Revision ID: 0007_iam_governance
Revises: 0006_mdm_core
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_iam_governance"
down_revision = "0006_mdm_core"
branch_labels = None
depends_on = None


def upgrade():
    # --- Scoped RBAC grants (auth_user_role) ---
    with op.batch_alter_table("auth_user_role") as batch:
        # Add columns with defaults so existing rows migrate cleanly
        batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
        batch.add_column(sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="TENANT"))
        batch.add_column(sa.Column("scope_id", sa.String(length=64), nullable=False, server_default="default"))

        batch.create_index("ix_auth_user_role_tenant_id", ["tenant_id"], unique=False)
        batch.create_index("ix_auth_user_role_scope_type", ["scope_type"], unique=False)
        batch.create_index("ix_auth_user_role_scope_id", ["scope_id"], unique=False)

        # Drop old uniqueness (user_id, role_id) and replace with scoped grant uniqueness
        try:
            batch.drop_index("uq_auth_user_role_user_role")
        except Exception:
            pass
        batch.create_index(
            "uq_auth_user_role_grant",
            ["tenant_id", "user_id", "role_id", "scope_type", "scope_id"],
            unique=True,
        )

    # --- Refresh tokens ---
    op.create_table(
        "auth_refresh_token",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default", index=True),
        sa.Column("user_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
    )
    op.create_index("ix_refresh_token_tenant_user", "auth_refresh_token", ["tenant_id", "user_id"], unique=False)

    op.create_table(
        "auth_revoked_jti",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default", index=True),
        sa.Column("jti", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_revoked_jti_tenant_time", "auth_revoked_jti", ["tenant_id", "revoked_at"], unique=False)

    # --- Audit context fields ---
    with op.batch_alter_table("sys_audit_log") as batch:
        batch.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("ip_address", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("user_agent", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("status_code", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch.create_index("ix_sys_audit_log_request_id", ["request_id"], unique=False)


def downgrade():
    # Reverse audit columns
    with op.batch_alter_table("sys_audit_log") as batch:
        try:
            batch.drop_index("ix_sys_audit_log_request_id")
        except Exception:
            pass
        batch.drop_column("success")
        batch.drop_column("status_code")
        batch.drop_column("user_agent")
        batch.drop_column("ip_address")
        batch.drop_column("request_id")

    op.drop_index("ix_revoked_jti_tenant_time", table_name="auth_revoked_jti")
    op.drop_table("auth_revoked_jti")
    op.drop_index("ix_refresh_token_tenant_user", table_name="auth_refresh_token")
    op.drop_table("auth_refresh_token")

    with op.batch_alter_table("auth_user_role") as batch:
        try:
            batch.drop_index("uq_auth_user_role_grant")
        except Exception:
            pass
        # Restore old uniqueness
        batch.create_index("uq_auth_user_role_user_role", ["user_id", "role_id"], unique=True)
        batch.drop_column("scope_id")
        batch.drop_column("scope_type")
        batch.drop_column("tenant_id")

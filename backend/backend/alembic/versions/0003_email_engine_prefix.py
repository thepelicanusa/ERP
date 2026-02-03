"""Prefix email engine tables (ee_*) to avoid conflicts.

Revision ID: 0003_email_engine_prefix
Revises: 0002_auth_rbac
Create Date: 2026-02-01

This migration is designed to be safe in early-stage deployments:
- Creates the new ee_* tables
- Best-effort copies data from legacy tables (email_*) if they exist
- Drops legacy tables

If you already have production data in legacy tables, consider taking a backup
before running migrations.
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_email_engine_prefix"
down_revision = "0002_auth_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New prefixed tables
    op.create_table(
        "ee_email_account",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_name", sa.String(length=64), nullable=False, index=True),
        sa.Column("email_address", sa.String(length=256), nullable=False, unique=True, index=True),
        sa.Column("smtp_host", sa.String(length=256), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_tls", sa.Boolean(), nullable=False),
        sa.Column("smtp_username", sa.String(length=256), nullable=False),
        sa.Column("smtp_password_enc", sa.Text(), nullable=False),
        sa.Column("imap_host", sa.String(length=256), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False),
        sa.Column("imap_tls", sa.Boolean(), nullable=False),
        sa.Column("imap_username", sa.String(length=256), nullable=False),
        sa.Column("imap_password_enc", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
    )

    op.create_table(
        "ee_email_message",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False, index=True),
        sa.Column("status", sa.String(length=16), nullable=False, index=True),
        sa.Column("owner_user_name", sa.String(length=64), nullable=False, index=True),
        sa.Column("from_email", sa.String(length=256), nullable=False),
        sa.Column("to_emails", sa.JSON(), nullable=False),
        sa.Column("cc_emails", sa.JSON(), nullable=False),
        sa.Column("bcc_emails", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("smtp_message_id", sa.String(length=512), nullable=True, index=True),
        sa.Column("in_reply_to", sa.String(length=512), nullable=True, index=True),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("correlation_token", sa.String(length=128), nullable=True, index=True),
        sa.Column("thread_key", sa.String(length=128), nullable=True, index=True),
        sa.Column("erp_model", sa.String(length=64), nullable=True, index=True),
        sa.Column("erp_record_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
    )

    op.create_table(
        "ee_email_attachment",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_id", sa.String(length=36), sa.ForeignKey("ee_email_message.id"), nullable=False, index=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False, index=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
    )

    op.create_table(
        "ee_email_event",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_id", sa.String(length=36), sa.ForeignKey("ee_email_message.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )

    op.create_table(
        "ee_email_triage",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inbound_message_id", sa.String(length=36), sa.ForeignKey("ee_email_message.id"), nullable=False, index=True),
        sa.Column("status", sa.String(length=16), nullable=False, index=True),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("suggested_model", sa.String(length=64), nullable=True),
        sa.Column("suggested_record_id", sa.String(length=64), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
    )
    op.create_index("ix_ee_email_triage_status_created", "ee_email_triage", ["status", "created_at"])

    # Best-effort data copy from legacy tables (if they exist)
    _copy_if_exists("email_account", "ee_email_account")
    _copy_if_exists("email_message", "ee_email_message")
    _copy_if_exists("email_attachment", "ee_email_attachment")
    _copy_if_exists("email_event", "ee_email_event")
    _copy_if_exists("email_triage", "ee_email_triage")

    # Drop legacy tables (ignore errors if they don't exist)
    for t in ["email_triage", "email_event", "email_attachment", "email_message", "email_account"]:
        try:
            op.drop_table(t)
        except Exception:
            pass


def downgrade() -> None:
    # Downgrade strategy: simply drop ee_* tables.
    # (Recreating legacy tables is intentionally omitted.)
    try:
        op.drop_index("ix_ee_email_triage_status_created", table_name="ee_email_triage")
    except Exception:
        pass
    for t in ["ee_email_triage", "ee_email_event", "ee_email_attachment", "ee_email_message", "ee_email_account"]:
        try:
            op.drop_table(t)
        except Exception:
            pass


def _copy_if_exists(src: str, dst: str) -> None:
    """Copy rows from src to dst if src exists.

    Uses INSERT INTO dst SELECT * FROM src, relying on matching schemas.
    If schemas diverge or src doesn't exist, it no-ops.
    """
    try:
        op.execute(f"INSERT INTO {dst} SELECT * FROM {src}")
    except Exception:
        # src may not exist or columns may differ; ignore in early-stage setups
        pass

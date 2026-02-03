"""event bus webhook subscriptions + outbox delivery state

Revision ID: 0005_event_bus_webhooks
Revises: 0004_create_all_tables
Create Date: 2026-02-01T23:58:00.000000Z
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_event_bus_webhooks"
down_revision = "0004_create_all_tables"
branch_labels = None
depends_on = None


def upgrade():
    # outbox_event columns (if you already created the table with 0004)
    with op.batch_alter_table("outbox_event") as batch:
        batch.add_column(sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch.add_column(sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_error", sa.Text(), nullable=True))
        batch.add_column(sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_outbox_delivery", "outbox_event", ["delivered", "available_at"], unique=False)

    op.create_table(
        "event_subscription",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("topic_pattern", sa.String(length=128), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_event_sub_active", "event_subscription", ["is_active", "topic_pattern"], unique=False)


def downgrade():
    op.drop_index("ix_event_sub_active", table_name="event_subscription")
    op.drop_table("event_subscription")

    op.drop_index("ix_outbox_delivery", table_name="outbox_event")
    with op.batch_alter_table("outbox_event") as batch:
        batch.drop_column("delivered_at")
        batch.drop_column("delivered")
        batch.drop_column("last_error")
        batch.drop_column("attempt_count")
        batch.drop_column("available_at")
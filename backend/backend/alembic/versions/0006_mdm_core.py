"""mdm core tables

Revision ID: 0006_mdm_core
Revises: 0005_event_bus_webhooks
Create Date: 2026-02-02T00:45:00Z
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_mdm_core"
down_revision = "0005_event_bus_webhooks"
branch_labels = None
depends_on = None


def upgrade():
    # Org units (ISA-95 hierarchy)
    op.create_table(
        "mdm_org_unit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("mdm_org_unit.id"), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("type", "code", name="uq_mdm_org_unit_type_code"),
    )

    op.create_table(
        "mdm_uom",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
    )

    op.create_table(
        "mdm_item_class",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
    )

    op.create_table(
        "mdm_item",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("item_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("uom_id", sa.String(length=36), sa.ForeignKey("mdm_uom.id"), nullable=False),
        sa.Column("class_id", sa.String(length=36), sa.ForeignKey("mdm_item_class.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("revision", sa.String(length=32), nullable=False, server_default="A"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "mdm_party",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("party_type", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
    )

    op.create_table(
        "mdm_person",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("employee_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("org_unit_id", sa.String(length=36), sa.ForeignKey("mdm_org_unit.id"), nullable=True),
    )

    op.create_table(
        "mdm_equipment",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("equipment_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("equipment_type", sa.String(length=64), nullable=False, server_default="GENERIC"),
        sa.Column("org_unit_id", sa.String(length=36), sa.ForeignKey("mdm_org_unit.id"), nullable=True),
    )

    op.create_index("ix_mdm_org_unit_parent", "mdm_org_unit", ["parent_id"], unique=False)
    op.create_index("ix_mdm_item_uom", "mdm_item", ["uom_id"], unique=False)
    op.create_index("ix_mdm_item_class", "mdm_item", ["class_id"], unique=False)


def downgrade():
    op.drop_index("ix_mdm_item_class", table_name="mdm_item")
    op.drop_index("ix_mdm_item_uom", table_name="mdm_item")
    op.drop_index("ix_mdm_org_unit_parent", table_name="mdm_org_unit")

    op.drop_table("mdm_equipment")
    op.drop_table("mdm_person")
    op.drop_table("mdm_party")
    op.drop_table("mdm_item")
    op.drop_table("mdm_item_class")
    op.drop_table("mdm_uom")
    op.drop_table("mdm_org_unit")

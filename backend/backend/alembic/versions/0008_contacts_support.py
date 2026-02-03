"""Contacts + Support foundation (Party + Legal Entity + Profiles + Tickets).

Revision ID: 0008_contacts_support
Revises: 0007_iam_governance
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_contacts_support"
down_revision = "0007_iam_governance"
branch_labels = None
depends_on = None


def upgrade():
    # --- Contacts ---
    op.create_table(
        "legal_entity",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),
    )
    op.create_index("ix_legal_entity_tenant_id", "legal_entity", ["tenant_id"])

    op.create_table(
        "party",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("party_type", sa.Enum("PERSON", "ORG", name="partytype"), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("tax_id", sa.String(length=64), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_party_tenant_id", "party", ["tenant_id"])
    op.create_index("ix_party_display_name", "party", ["display_name"])
    op.create_index("ix_party_tax_id", "party", ["tax_id"])

    op.create_table(
        "party_profile",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("legal_entity_id", sa.String(length=36), sa.ForeignKey("legal_entity.id"), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("party.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("account_owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("legal_entity_id", "party_id", name="uq_party_profile_legal_entity_party"),
    )
    op.create_index("ix_party_profile_tenant_id", "party_profile", ["tenant_id"])
    op.create_index("ix_party_profile_legal_entity_id", "party_profile", ["legal_entity_id"])
    op.create_index("ix_party_profile_party_id", "party_profile", ["party_id"])
    op.create_index("ix_party_profile_tenant_legal_entity_party", "party_profile", ["tenant_id", "legal_entity_id", "party_id"])

    op.create_table(
        "party_profile_role",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("party_profile_id", sa.String(length=36), sa.ForeignKey("party_profile.id"), nullable=False),
        sa.Column("role", sa.Enum("CUSTOMER", "VENDOR", name="partyrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("party_profile_id", "role", name="uq_party_profile_role"),
    )
    op.create_index("ix_party_profile_role_party_profile_id", "party_profile_role", ["party_profile_id"])

    op.create_table(
        "customer_profile",
        sa.Column("party_profile_id", sa.String(length=36), sa.ForeignKey("party_profile.id"), primary_key=True),
        sa.Column("payment_terms", sa.String(length=64), nullable=True),
        sa.Column("credit_limit", sa.Float(), nullable=True),
    )
    op.create_table(
        "vendor_profile",
        sa.Column("party_profile_id", sa.String(length=36), sa.ForeignKey("party_profile.id"), primary_key=True),
        sa.Column("payment_terms", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "party_contact_method",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("party.id"), nullable=False),
        sa.Column("type", sa.Enum("EMAIL", "PHONE", "OTHER", name="contactmethodtype"), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_party_contact_method_party_id", "party_contact_method", ["party_id"])
    op.create_index("ix_party_contact_method_value", "party_contact_method", ["value"])

    op.create_table(
        "party_address",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("party.id"), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("line1", sa.String(length=255), nullable=False),
        sa.Column("line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_party_address_party_id", "party_address", ["party_id"])

    op.create_table(
        "party_relationship",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("party.id"), nullable=False),
        sa.Column("related_party_id", sa.String(length=36), sa.ForeignKey("party.id"), nullable=False),
        sa.Column("relationship_type", sa.Enum("EMPLOYEE_OF", "CONTACT_FOR", "RELATED", name="relationshiptype"), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_party_relationship_tenant_id", "party_relationship", ["tenant_id"])
    op.create_index("ix_party_relationship_party_id", "party_relationship", ["party_id"])
    op.create_index("ix_party_relationship_related_party_id", "party_relationship", ["related_party_id"])
    op.create_index("ix_party_relationship_tenant_party_related", "party_relationship", ["tenant_id", "party_id", "related_party_id"])

    # --- Support ---
    op.create_table(
        "support_ticket",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("legal_entity_id", sa.String(length=36), nullable=True),
        sa.Column("party_profile_id", sa.String(length=36), sa.ForeignKey("party_profile.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("OPEN", "IN_PROGRESS", "WAITING", "RESOLVED", "CLOSED", name="ticketstatus"), nullable=False),
        sa.Column("priority", sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="ticketpriority"), nullable=False),
        sa.Column("assigned_user_id", sa.String(length=64), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_support_ticket_tenant_id", "support_ticket", ["tenant_id"])
    op.create_index("ix_support_ticket_party_profile_id", "support_ticket", ["party_profile_id"])
    op.create_index("ix_support_ticket_status", "support_ticket", ["status"])
    op.create_index("ix_support_ticket_priority", "support_ticket", ["priority"])
    op.create_index("ix_support_ticket_tenant_status_priority", "support_ticket", ["tenant_id", "status", "priority"])

    op.create_table(
        "support_ticket_comment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.String(length=36), sa.ForeignKey("support_ticket.id"), nullable=False),
        sa.Column("author_user_id", sa.String(length=64), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_support_ticket_comment_ticket_id", "support_ticket_comment", ["ticket_id"])


def downgrade():
    op.drop_index("ix_support_ticket_comment_ticket_id", table_name="support_ticket_comment")
    op.drop_table("support_ticket_comment")

    op.drop_index("ix_support_ticket_tenant_status_priority", table_name="support_ticket")
    op.drop_index("ix_support_ticket_priority", table_name="support_ticket")
    op.drop_index("ix_support_ticket_status", table_name="support_ticket")
    op.drop_index("ix_support_ticket_party_profile_id", table_name="support_ticket")
    op.drop_index("ix_support_ticket_tenant_id", table_name="support_ticket")
    op.drop_table("support_ticket")

    op.drop_index("ix_party_relationship_tenant_party_related", table_name="party_relationship")
    op.drop_index("ix_party_relationship_related_party_id", table_name="party_relationship")
    op.drop_index("ix_party_relationship_party_id", table_name="party_relationship")
    op.drop_index("ix_party_relationship_tenant_id", table_name="party_relationship")
    op.drop_table("party_relationship")

    op.drop_index("ix_party_address_party_id", table_name="party_address")
    op.drop_table("party_address")

    op.drop_index("ix_party_contact_method_value", table_name="party_contact_method")
    op.drop_index("ix_party_contact_method_party_id", table_name="party_contact_method")
    op.drop_table("party_contact_method")

    op.drop_table("vendor_profile")
    op.drop_table("customer_profile")

    op.drop_index("ix_party_profile_role_party_profile_id", table_name="party_profile_role")
    op.drop_table("party_profile_role")

    op.drop_index("ix_party_profile_tenant_legal_entity_party", table_name="party_profile")
    op.drop_index("ix_party_profile_party_id", table_name="party_profile")
    op.drop_index("ix_party_profile_legal_entity_id", table_name="party_profile")
    op.drop_index("ix_party_profile_tenant_id", table_name="party_profile")
    op.drop_table("party_profile")

    op.drop_index("ix_party_tax_id", table_name="party")
    op.drop_index("ix_party_display_name", table_name="party")
    op.drop_index("ix_party_tenant_id", table_name="party")
    op.drop_table("party")

    op.drop_index("ix_legal_entity_tenant_id", table_name="legal_entity")
    op.drop_table("legal_entity")

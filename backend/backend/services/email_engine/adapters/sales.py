from __future__ import annotations

"""Sales adapter for the email engine.

All Sales-specific imports live in this file only, to prevent cross-module
conflicts in a multi-module ERP.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.sales import Customer, SalesOrder, SalesOrderLine

from ..core_extract import email_only


def try_create_sales_order_from_email(
    *,
    db: Session,
    owner_user_name: str,
    from_email: str,
    subject: str,
    body_text: str,
    attachment_text: str,
) -> Optional[SalesOrder]:
    """Best-effort creation of a draft Sales Order from an inbound email.

    Phase-1 behavior:
      - Identify customer by sender email
      - Create a draft sales order linked to the email
      - Create a single placeholder line (until PO parsing is added)
    """

    sender = email_only(from_email)
    if not sender:
        return None

    customer = db.query(Customer).filter(Customer.email == sender).first()
    if customer is None:
        return None

    so = SalesOrder(
        customer_id=customer.id,
        status="DRAFT",
        order_date=date.today(),
        currency=getattr(customer, "currency", "USD"),
        subtotal_amount=0,
        tax_amount=0,
        shipping_amount=0,
        total_amount=0,
        meta={
            "created_from_email": True,
            "email_owner": owner_user_name,
            "source_subject": subject,
        },
    )
    db.add(so)
    db.flush()

    # Placeholder line – you can replace this later with PO line extraction/mapping.
    line = SalesOrderLine(
        sales_order_id=so.id,
        product_id=None,
        description=f"Inbound PO email: {subject}" if subject else "Inbound PO email",
        quantity=1,
        unit_price=0,
        line_total=0,
        meta={"created_from_email": True},
    )
    db.add(line)
    db.flush()
    return so

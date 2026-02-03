"""
E-commerce API

REST API endpoints for e-commerce functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import secrets

from app.db.session import get_db
from app.core.security import get_principal

from app.db.models.ecommerce import (
    EcomCategory, EcomProduct, EcomProductVariant,
    EcomCustomer, EcomAddress, EcomCart, EcomCartItem,
    EcomOrder, EcomOrderItem, EcomProductReview,
    EcomPricingRule, EcomCoupon, EcomWishlist
)

router = APIRouter(prefix="/ecommerce", tags=["E-commerce"])

@router.get("/health")
def health():
    return {"ok": True, "service": "ecommerce"}


# ============================================================================
# CATALOG - Public endpoints
# ============================================================================

@router.get("/categories")
def list_categories(
    parent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List product categories"""
    query = db.query(EcomCategory).filter(EcomCategory.is_active == True)
    
    if parent_id:
        query = query.filter(EcomCategory.parent_id == parent_id)
    else:
        query = query.filter(EcomCategory.parent_id == None)
    
    categories = query.order_by(EcomCategory.sort_order).all()
    
    return [{
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "image_url": c.image_url,
        "sort_order": c.sort_order
    } for c in categories]


@router.get("/categories/{slug}")
def get_category(slug: str, db: Session = Depends(get_db)):
    """Get category by slug"""
    category = db.query(EcomCategory).filter(
        EcomCategory.slug == slug,
        EcomCategory.is_active == True
    ).first()
    
    if not category:
        raise HTTPException(404, "Category not found")
    
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "image_url": category.image_url,
        "meta_title": category.meta_title,
        "meta_description": category.meta_description
    }


@router.get("/products")
def list_products(
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    featured: Optional[bool] = None,
    sort: str = "newest",  # newest, price_asc, price_desc, popular
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List products with filtering and pagination"""
    query = db.query(EcomProduct).filter(EcomProduct.is_active == True)
    
    # Filters
    if category_id:
        query = query.filter(EcomProduct.category_id == category_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (EcomProduct.name.ilike(search_term)) |
            (EcomProduct.short_description.ilike(search_term)) |
            (EcomProduct.sku.ilike(search_term))
        )
    
    if min_price:
        query = query.filter(EcomProduct.price >= min_price)
    
    if max_price:
        query = query.filter(EcomProduct.price <= max_price)
    
    if featured is not None:
        query = query.filter(EcomProduct.is_featured == featured)
    
    # Sorting
    if sort == "price_asc":
        query = query.order_by(EcomProduct.price.asc())
    elif sort == "price_desc":
        query = query.order_by(EcomProduct.price.desc())
    elif sort == "popular":
        query = query.order_by(EcomProduct.sales_count.desc())
    else:  # newest
        query = query.order_by(EcomProduct.created_at.desc())
    
    # Total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()
    
    return {
        "products": [{
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "sku": p.sku,
            "short_description": p.short_description,
            "price": float(p.price),
            "compare_at_price": float(p.compare_at_price) if p.compare_at_price else None,
            "primary_image_url": p.primary_image_url,
            "is_featured": p.is_featured,
            "category_id": p.category_id,
            "tags": p.tags
        } for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/products/{slug}")
def get_product(slug: str, db: Session = Depends(get_db)):
    """Get product details by slug"""
    product = db.query(EcomProduct).filter(
        EcomProduct.slug == slug,
        EcomProduct.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    
    # Get variants
    variants = db.query(EcomProductVariant).filter(
        EcomProductVariant.product_id == product.id,
        EcomProductVariant.is_active == True
    ).order_by(EcomProductVariant.sort_order).all()
    
    # Get reviews
    reviews = db.query(EcomProductReview).filter(
        EcomProductReview.product_id == product.id,
        EcomProductReview.is_approved == True
    ).order_by(desc(EcomProductReview.created_at)).limit(10).all()
    
    # Average rating
    avg_rating = db.query(func.avg(EcomProductReview.rating)).filter(
        EcomProductReview.product_id == product.id,
        EcomProductReview.is_approved == True
    ).scalar() or 0
    
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "short_description": product.short_description,
        "long_description": product.long_description,
        "price": float(product.price),
        "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
        "primary_image_url": product.primary_image_url,
        "images": product.images,
        "is_featured": product.is_featured,
        "category_id": product.category_id,
        "tags": product.tags,
        "attributes": product.attributes,
        "weight": float(product.weight) if product.weight else None,
        "weight_unit": product.weight_unit,
        "meta_title": product.meta_title,
        "meta_description": product.meta_description,
        "variants": [{
            "id": v.id,
            "sku": v.sku,
            "name": v.name,
            "attributes": v.attributes,
            "price": float(v.price) if v.price else float(product.price),
            "stock_quantity": v.stock_quantity,
            "image_url": v.image_url
        } for v in variants],
        "reviews": {
            "average_rating": float(avg_rating),
            "total_reviews": len(reviews),
            "reviews": [{
                "rating": r.rating,
                "title": r.title,
                "review_text": r.review_text,
                "created_at": r.created_at.isoformat(),
                "helpful_count": r.helpful_count
            } for r in reviews]
        },
        "view_count": product.view_count,
        "sales_count": product.sales_count
    }


# ============================================================================
# CART - Session-based or customer
# ============================================================================

@router.post("/cart")
def create_cart(
    customer_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new shopping cart"""
    if not session_id:
        session_id = secrets.token_urlsafe(32)
    
    cart = EcomCart(
        customer_id=customer_id,
        session_id=session_id,
        status="ACTIVE"
    )
    db.add(cart)
    db.commit()
    db.refresh(cart)
    
    return {
        "id": cart.id,
        "session_id": cart.session_id,
        "subtotal": float(cart.subtotal),
        "total": float(cart.total)
    }


@router.get("/cart/{cart_id}")
def get_cart(cart_id: str, db: Session = Depends(get_db)):
    """Get cart details"""
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    
    if not cart:
        raise HTTPException(404, "Cart not found")
    
    items = db.query(EcomCartItem).filter(EcomCartItem.cart_id == cart_id).all()
    
    return {
        "id": cart.id,
        "subtotal": float(cart.subtotal),
        "tax_amount": float(cart.tax_amount),
        "shipping_amount": float(cart.shipping_amount),
        "discount_amount": float(cart.discount_amount),
        "total": float(cart.total),
        "coupon_code": cart.coupon_code,
        "items": [{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "product_sku": item.product_sku,
            "product_image": item.product_image,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "line_total": float(item.line_total)
        } for item in items],
        "item_count": len(items)
    }


@router.post("/cart/{cart_id}/items")
def add_to_cart(
    cart_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")
    
    product_id = payload.get("product_id")
    variant_id = payload.get("variant_id")
    quantity = payload.get("quantity", 1)
    
    # Get product
    product = db.query(EcomProduct).filter(EcomProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Determine price
    unit_price = product.price
    product_name = product.name
    product_sku = product.sku
    
    if variant_id:
        variant = db.query(EcomProductVariant).filter(EcomProductVariant.id == variant_id).first()
        if variant and variant.price:
            unit_price = variant.price
        product_sku = variant.sku if variant else product_sku
    
    # Check if item already in cart
    existing = db.query(EcomCartItem).filter(
        EcomCartItem.cart_id == cart_id,
        EcomCartItem.product_id == product_id,
        EcomCartItem.variant_id == variant_id
    ).first()
    
    if existing:
        # Update quantity
        existing.quantity += quantity
        existing.line_total = existing.unit_price * existing.quantity
        db.commit()
        item = existing
    else:
        # Add new item
        item = EcomCartItem(
            cart_id=cart_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            line_total=unit_price * quantity,
            product_name=product_name,
            product_sku=product_sku,
            product_image=product.primary_image_url
        )
        db.add(item)
        db.commit()
    
    # Recalculate cart totals
    _recalculate_cart(cart, db)
    
    return {
        "id": item.id,
        "quantity": item.quantity,
        "line_total": float(item.line_total)
    }


@router.patch("/cart/{cart_id}/items/{item_id}")
def update_cart_item(
    cart_id: str,
    item_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    item = db.query(EcomCartItem).filter(
        EcomCartItem.id == item_id,
        EcomCartItem.cart_id == cart_id
    ).first()
    
    if not item:
        raise HTTPException(404, "Cart item not found")
    
    quantity = payload.get("quantity", item.quantity)
    
    if quantity <= 0:
        db.delete(item)
    else:
        item.quantity = quantity
        item.line_total = item.unit_price * quantity
    
    db.commit()
    
    # Recalculate cart
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    _recalculate_cart(cart, db)
    
    return {"success": True}


@router.delete("/cart/{cart_id}/items/{item_id}")
def remove_from_cart(cart_id: str, item_id: str, db: Session = Depends(get_db)):
    """Remove item from cart"""
    item = db.query(EcomCartItem).filter(
        EcomCartItem.id == item_id,
        EcomCartItem.cart_id == cart_id
    ).first()
    
    if not item:
        raise HTTPException(404, "Cart item not found")
    
    db.delete(item)
    db.commit()
    
    # Recalculate cart
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    _recalculate_cart(cart, db)
    
    return {"success": True}


@router.post("/cart/{cart_id}/apply-coupon")
def apply_coupon(cart_id: str, payload: dict, db: Session = Depends(get_db)):
    """Apply coupon code to cart"""
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")
    
    code = payload.get("code", "").upper()
    
    coupon = db.query(EcomCoupon).filter(
        EcomCoupon.code == code,
        EcomCoupon.is_active == True
    ).first()
    
    if not coupon:
        raise HTTPException(400, "Invalid coupon code")
    
    # Check validity dates
    now = datetime.utcnow()
    if coupon.valid_from and now < coupon.valid_from:
        raise HTTPException(400, "Coupon not yet valid")
    if coupon.valid_until and now > coupon.valid_until:
        raise HTTPException(400, "Coupon expired")
    
    # Check usage limits
    if coupon.usage_limit_total and coupon.usage_count >= coupon.usage_limit_total:
        raise HTTPException(400, "Coupon usage limit reached")
    
    # Check minimum purchase
    if coupon.min_purchase_amount and cart.subtotal < coupon.min_purchase_amount:
        raise HTTPException(400, f"Minimum purchase of ${coupon.min_purchase_amount} required")
    
    cart.coupon_code = code
    db.commit()
    
    # Recalculate with discount
    _recalculate_cart(cart, db)
    
    return {
        "success": True,
        "discount_amount": float(cart.discount_amount)
    }


# ============================================================================
# ORDERS
# ============================================================================

@router.post("/orders")
def create_order(payload: dict, db: Session = Depends(get_db)):
    """Create order from cart"""
    cart_id = payload.get("cart_id")
    customer_id = payload.get("customer_id")
    
    cart = db.query(EcomCart).filter(EcomCart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")
    
    customer = db.query(EcomCustomer).filter(EcomCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    cart_items = db.query(EcomCartItem).filter(EcomCartItem.cart_id == cart_id).all()
    if not cart_items:
        raise HTTPException(400, "Cart is empty")
    
    # Generate order number
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
    
    # Create order
    order = EcomOrder(
        order_number=order_number,
        customer_id=customer_id,
        status="PENDING",
        payment_status="PENDING",
        fulfillment_status="UNFULFILLED",
        subtotal=cart.subtotal,
        tax_amount=cart.tax_amount,
        shipping_amount=cart.shipping_amount,
        discount_amount=cart.discount_amount,
        total=cart.total,
        coupon_code=cart.coupon_code,
        billing_address=payload.get("billing_address", {}),
        shipping_address=payload.get("shipping_address", {}),
        customer_email=customer.email,
        customer_name=f"{customer.first_name} {customer.last_name}",
        customer_phone=customer.phone,
        payment_method=payload.get("payment_method"),
        shipping_method=payload.get("shipping_method"),
        customer_notes=payload.get("notes")
    )
    db.add(order)
    db.flush()
    
    # Create order items
    for cart_item in cart_items:
        order_item = EcomOrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            variant_id=cart_item.variant_id,
            product_name=cart_item.product_name,
            product_sku=cart_item.product_sku,
            product_image=cart_item.product_image,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            line_total=cart_item.line_total
        )
        db.add(order_item)
    
    # Mark cart as converted
    cart.status = "CONVERTED"
    
    db.commit()
    db.refresh(order)
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "total": float(order.total),
        "status": order.status
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get order details"""
    order = db.query(EcomOrder).filter(EcomOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(404, "Order not found")
    
    items = db.query(EcomOrderItem).filter(EcomOrderItem.order_id == order_id).all()
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "fulfillment_status": order.fulfillment_status,
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "shipping_amount": float(order.shipping_amount),
        "discount_amount": float(order.discount_amount),
        "total": float(order.total),
        "billing_address": order.billing_address,
        "shipping_address": order.shipping_address,
        "shipping_method": order.shipping_method,
        "tracking_number": order.tracking_number,
        "order_date": order.order_date.isoformat(),
        "items": [{
            "product_name": item.product_name,
            "product_sku": item.product_sku,
            "product_image": item.product_image,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "line_total": float(item.line_total)
        } for item in items]
    }


@router.get("/customers/{customer_id}/orders")
def get_customer_orders(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get customer order history"""
    query = db.query(EcomOrder).filter(EcomOrder.customer_id == customer_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    
    orders = query.order_by(desc(EcomOrder.order_date)).offset(offset).limit(page_size).all()
    
    return {
        "orders": [{
            "id": o.id,
            "order_number": o.order_number,
            "order_date": o.order_date.isoformat(),
            "status": o.status,
            "total": float(o.total),
            "item_count": db.query(EcomOrderItem).filter(EcomOrderItem.order_id == o.id).count()
        } for o in orders],
        "total": total,
        "page": page,
        "total_pages": (total + page_size - 1) // page_size
    }


# ============================================================================
# REVIEWS
# ============================================================================

@router.post("/reviews")
def create_review(payload: dict, db: Session = Depends(get_db)):
    """Create product review"""
    product_id = payload.get("product_id")
    customer_id = payload.get("customer_id")
    
    # Check if customer already reviewed this product
    existing = db.query(EcomProductReview).filter(
        EcomProductReview.product_id == product_id,
        EcomProductReview.customer_id == customer_id
    ).first()
    
    if existing:
        raise HTTPException(400, "You have already reviewed this product")
    
    review = EcomProductReview(
        product_id=product_id,
        customer_id=customer_id,
        order_id=payload.get("order_id"),
        rating=payload.get("rating"),
        title=payload.get("title"),
        review_text=payload.get("review_text"),
        is_approved=False  # Requires moderation
    )
    db.add(review)
    db.commit()
    
    return {"id": review.id, "status": "pending_approval"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _recalculate_cart(cart: EcomCart, db: Session):
    """Recalculate cart totals"""
    items = db.query(EcomCartItem).filter(EcomCartItem.cart_id == cart.id).all()
    
    subtotal = sum(item.line_total for item in items)
    cart.subtotal = subtotal
    
    # Calculate discount
    discount = Decimal(0)
    if cart.coupon_code:
        coupon = db.query(EcomCoupon).filter(EcomCoupon.code == cart.coupon_code).first()
        if coupon:
            if coupon.discount_type == "PERCENTAGE":
                discount = subtotal * (coupon.discount_value / 100)
            elif coupon.discount_type == "FIXED_AMOUNT":
                discount = coupon.discount_value
            
            if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                discount = coupon.max_discount_amount
    
    cart.discount_amount = discount
    
    # Tax calculation (simplified - would integrate with tax service)
    taxable_amount = subtotal - discount
    cart.tax_amount = taxable_amount * Decimal("0.08")  # Example 8% tax
    
    # Shipping (simplified - would integrate with shipping service)
    cart.shipping_amount = Decimal("10.00") if subtotal < 100 else Decimal("0")
    
    cart.total = subtotal + cart.tax_amount + cart.shipping_amount - discount
    
    db.commit()

from flask import Blueprint, render_template, request, redirect, jsonify
from app.database import get_db
from app.models import Product, CartItem, Favorite, Order
from app.auth import get_current_user

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("", methods=["GET"])
@cart_bp.route("/", methods=["GET"])
def cart_page():
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    total = sum(i.product.price * i.quantity for i in items)
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return render_template("cart.html", user=user, items=items, total=total,
                           cart_count=len(items), fav_count=fav_count, success=None)


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    db = get_db()
    user = get_current_user(db)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    product = db.query(Product).filter_by(id=product_id, status="approved").first()
    if not product:
        return jsonify({"error": "not found"}), 404
    existing = db.query(CartItem).filter_by(user_id=user.id, product_id=product_id).first()
    if existing:
        existing.quantity += 1
    else:
        db.add(CartItem(user_id=user.id, product_id=product_id, quantity=1))
    db.commit()
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count()
    return jsonify({"success": True, "cart_count": cart_count})


@cart_bp.route("/update/<int:item_id>", methods=["POST"])
def update_cart(item_id):
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    quantity = int(request.form.get("quantity", 1))
    item = db.query(CartItem).filter_by(id=item_id, user_id=user.id).first()
    if item:
        if quantity < 1:
            db.delete(item)
        else:
            item.quantity = quantity
        db.commit()
    return redirect("/cart")


@cart_bp.route("/remove/<int:item_id>", methods=["POST"])
def remove_from_cart(item_id):
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    item = db.query(CartItem).filter_by(id=item_id, user_id=user.id).first()
    if item:
        db.delete(item)
        db.commit()
    return redirect("/cart")


@cart_bp.route("/checkout", methods=["GET"])
def checkout_page():
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    if not items:
        return redirect("/cart")
    total = sum(i.product.price * i.quantity for i in items)
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return render_template("checkout.html", user=user, items=items, total=total,
                           cart_count=len(items), fav_count=fav_count)


@cart_bp.route("/checkout", methods=["POST"])
def checkout():
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    if not items:
        return redirect("/cart")
    full_name = request.form.get("full_name", "")
    phone = request.form.get("phone", "")
    address = request.form.get("address", "")
    payment = request.form.get("payment", "")
    total = sum(i.product.price * i.quantity for i in items)
    order = Order(user_id=user.id, total=total, status="new")
    db.add(order)
    db.flush()
    for item in items:
        db.delete(item)
    db.commit()
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return render_template("order_success.html", user=user, order_id=order.id, total=total,
                           full_name=full_name, address=address, payment=payment,
                           cart_count=0, fav_count=fav_count)

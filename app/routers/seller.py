import os
import uuid
from flask import Blueprint, render_template, request, redirect
from app.database import get_db
from app.models import Product, Category, CartItem, Favorite
from app.auth import get_current_user

seller_bp = Blueprint("seller", __name__)
UPLOAD_DIR = "app/static/uploads"


def nav(user, db):
    if not user:
        return 0, 0
    return (
        db.query(CartItem).filter_by(user_id=user.id).count(),
        db.query(Favorite).filter_by(user_id=user.id).count(),
    )


@seller_bp.route("/dashboard", methods=["GET"])
def dashboard():
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    if user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    cart_count, fav_count = nav(user, db)
    my_products = db.query(Product).filter_by(seller_id=user.id).order_by(Product.created_at.desc()).all()
    return render_template("seller/dashboard.html", user=user, products=my_products,
                           cart_count=cart_count, fav_count=fav_count)


@seller_bp.route("/add", methods=["GET"])
def add_product_page():
    db = get_db()
    user = get_current_user(db)
    if not user or user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    cart_count, fav_count = nav(user, db)
    categories = db.query(Category).all()
    return render_template("seller/add_product.html", user=user, categories=categories,
                           cart_count=cart_count, fav_count=fav_count, error=None)


@seller_bp.route("/add", methods=["POST"])
def add_product():
    db = get_db()
    user = get_current_user(db)
    if not user or user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    name = request.form.get("name", "")
    description = request.form.get("description", "")
    price = float(request.form.get("price", 0))
    category_id = request.form.get("category_id", type=int)
    image = request.files.get("image")

    img_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            filename = f"{uuid.uuid4().hex}{ext}"
            image.save(os.path.join(UPLOAD_DIR, filename))
            img_url = f"/static/uploads/{filename}"

    db.add(Product(name=name, description=description, price=price,
                   category_id=category_id or None, seller_id=user.id,
                   img_url=img_url, status="pending"))
    db.commit()
    return redirect("/seller/dashboard")


@seller_bp.route("/edit/<int:product_id>", methods=["GET"])
def edit_product_page(product_id):
    db = get_db()
    user = get_current_user(db)
    if not user or user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if not product:
        return redirect("/seller/dashboard")
    categories = db.query(Category).all()
    cart_count, fav_count = nav(user, db)
    return render_template("seller/add_product.html", user=user, product=product,
                           categories=categories, cart_count=cart_count, fav_count=fav_count, error=None)


@seller_bp.route("/edit/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    db = get_db()
    user = get_current_user(db)
    if not user or user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if not product:
        return redirect("/seller/dashboard")
    image = request.files.get("image")
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            filename = f"{uuid.uuid4().hex}{ext}"
            image.save(os.path.join(UPLOAD_DIR, filename))
            product.img_url = f"/static/uploads/{filename}"
    product.name = request.form.get("name", product.name)
    product.description = request.form.get("description", "")
    product.price = float(request.form.get("price", product.price))
    product.category_id = request.form.get("category_id", type=int) or None
    product.status = "pending"
    db.commit()
    return redirect("/seller/dashboard")


@seller_bp.route("/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    db = get_db()
    user = get_current_user(db)
    if not user or user.role not in ("seller", "admin"):
        return redirect("/become-seller")
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if product:
        db.delete(product)
        db.commit()
    return redirect("/seller/dashboard")

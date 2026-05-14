from flask import Blueprint, render_template, request, redirect
from sqlalchemy import func
from app.database import get_db
from app.models import User, Product, Category
from app.auth import get_current_user

admin_bp = Blueprint("admin", __name__)


def require_admin(db):
    user = get_current_user(db)
    if not user or user.role != "admin":
        return None
    return user


@admin_bp.route("", methods=["GET"])
def admin_root():
    return redirect("/admin/dashboard")


@admin_bp.route("/dashboard", methods=["GET"])
def dashboard():
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    total_categories = db.query(Category).count()
    pending = db.query(Product).filter_by(status="pending").all()
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", user=user, total_users=total_users,
                           total_products=total_products, total_categories=total_categories,
                           pending=pending, recent_users=recent_users, cart_count=0, fav_count=0)


@admin_bp.route("/products", methods=["GET"])
def admin_products():
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    status = request.args.get("status")
    q = db.query(Product)
    if status and status != "all":
        q = q.filter(Product.status == status)
    items = q.order_by(Product.created_at.desc()).all()
    counts = {
        "all": db.query(Product).count(),
        "pending": db.query(Product).filter_by(status="pending").count(),
        "approved": db.query(Product).filter_by(status="approved").count(),
        "rejected": db.query(Product).filter_by(status="rejected").count(),
    }
    return render_template("admin/products.html", user=user, products=items,
                           status=status or "all", counts=counts, cart_count=0, fav_count=0)


@admin_bp.route("/products/<int:product_id>/approve", methods=["POST"])
def approve_product(product_id):
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        p.status = "approved"
        db.commit()
    return redirect("/admin/products?status=pending")


@admin_bp.route("/products/<int:product_id>/reject", methods=["POST"])
def reject_product(product_id):
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        p.status = "rejected"
        db.commit()
    return redirect("/admin/products?status=pending")


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        db.delete(p)
        db.commit()
    return redirect("/admin/products")


@admin_bp.route("/users", methods=["GET"])
def admin_users():
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    q_param = request.args.get("q")
    role = request.args.get("role")
    query = db.query(User)
    if q_param:
        query = query.filter(User.username.ilike(f"%{q_param}%"))
    if role and role != "all":
        query = query.filter(User.role == role)
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", user=user, users=users,
                           q=q_param or "", role=role or "all", cart_count=0, fav_count=0)


@admin_bp.route("/users/<int:user_id>/toggle-block", methods=["POST"])
def toggle_block(user_id):
    db = get_db()
    admin = require_admin(db)
    if not admin:
        return redirect("/auth/login")
    target = db.query(User).filter_by(id=user_id).first()
    if target and target.role != "admin":
        target.is_blocked = not target.is_blocked
        db.commit()
    return redirect("/admin/users")


@admin_bp.route("/users/<int:user_id>/change-role", methods=["POST"])
def change_role(user_id):
    db = get_db()
    admin = require_admin(db)
    if not admin:
        return redirect("/auth/login")
    target = db.query(User).filter_by(id=user_id).first()
    new_role = request.form.get("new_role", "")
    if target and target.id != admin.id and new_role in ("buyer", "seller"):
        target.role = new_role
        db.commit()
    return redirect("/admin/users")


@admin_bp.route("/categories", methods=["GET"])
def admin_categories():
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    cats = (
        db.query(Category, func.count(Product.id).label("cnt"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
        .all()
    )
    return render_template("admin/categories.html", user=user, categories=cats,
                           cart_count=0, fav_count=0, error=None)


@admin_bp.route("/categories/add", methods=["POST"])
def add_category():
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    name = request.form.get("name", "").strip()
    if name and not db.query(Category).filter_by(name=name).first():
        db.add(Category(name=name))
        db.commit()
    return redirect("/admin/categories")


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def delete_category(cat_id):
    db = get_db()
    user = require_admin(db)
    if not user:
        return redirect("/auth/login")
    cat = db.query(Category).filter_by(id=cat_id).first()
    if cat:
        db.query(Product).filter_by(category_id=cat_id).update({"category_id": None})
        db.delete(cat)
        db.commit()
    return redirect("/admin/categories")

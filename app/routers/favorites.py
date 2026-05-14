from flask import Blueprint, render_template, redirect, jsonify
from app.database import get_db
from app.models import Product, CartItem, Favorite
from app.auth import get_current_user

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("", methods=["GET"])
@favorites_bp.route("/", methods=["GET"])
def favorites_page():
    db = get_db()
    user = get_current_user(db)
    if not user:
        return redirect("/auth/login")
    favs = db.query(Favorite).filter_by(user_id=user.id).all()
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count()
    return render_template("favorites.html", user=user, favorites=favs,
                           cart_count=cart_count, fav_count=len(favs))


@favorites_bp.route("/toggle/<int:product_id>", methods=["POST"])
def toggle_favorite(product_id):
    db = get_db()
    user = get_current_user(db)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    existing = db.query(Favorite).filter_by(user_id=user.id, product_id=product_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    else:
        product = db.query(Product).filter_by(id=product_id, status="approved").first()
        if not product:
            return jsonify({"error": "not found"}), 404
        db.add(Favorite(user_id=user.id, product_id=product_id))
        db.commit()
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return jsonify({"success": True, "is_favorite": not existing, "fav_count": fav_count})

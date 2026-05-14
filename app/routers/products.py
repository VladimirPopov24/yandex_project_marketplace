from flask import Blueprint, render_template, request, redirect
from app.database import get_db
from app.models import Product, Category, CartItem, Favorite
from app.auth import get_current_user

products_bp = Blueprint("products", __name__)


def nav(user, db):
    if not user:
        return 0, 0
    return (
        db.query(CartItem).filter_by(user_id=user.id).count(),
        db.query(Favorite).filter_by(user_id=user.id).count(),
    )


@products_bp.route("", methods=["GET"])
@products_bp.route("/", methods=["GET"])
def products_list():
    db = get_db()
    user = get_current_user(db)
    cart_count, fav_count = nav(user, db)

    q = request.args.get("q")
    category_id = request.args.get("category_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "newest")
    page = max(1, request.args.get("page", 1, type=int))

    query = db.query(Product).filter(Product.status == "approved")
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    per_page = 24
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    categories = db.query(Category).all()
    fav_ids = {f.product_id for f in db.query(Favorite).filter_by(user_id=user.id).all()} if user else set()

    return render_template("products.html",
        user=user, products=items, categories=categories,
        cart_count=cart_count, fav_count=fav_count, fav_ids=fav_ids,
        q=q or "", selected_category=category_id, min_price=min_price or "",
        max_price=max_price or "", sort=sort, page=page, pages=pages, total=total)


@products_bp.route("/<int:product_id>", methods=["GET"])
def product_detail(product_id):
    db = get_db()
    user = get_current_user(db)
    cart_count, fav_count = nav(user, db)

    product = db.query(Product).filter_by(id=product_id, status="approved").first()
    if not product:
        return redirect("/products")

    is_favorite = bool(
        user and db.query(Favorite).filter_by(user_id=user.id, product_id=product_id).first()
    )
    related = (
        db.query(Product)
        .filter(Product.category_id == product.category_id,
                Product.id != product_id,
                Product.status == "approved")
        .limit(4).all()
    )

    return render_template("product_detail.html",
        user=user, product=product, is_favorite=is_favorite,
        related=related, cart_count=cart_count, fav_count=fav_count)

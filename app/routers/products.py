from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Category, CartItem, Favorite
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def nav(user, db):
    if not user:
        return 0, 0
    return (
        db.query(CartItem).filter_by(user_id=user.id).count(),
        db.query(Favorite).filter_by(user_id=user.id).count(),
    )


@router.get("", response_class=HTMLResponse)
async def products_list(
    request: Request,
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    sort: Optional[str] = Query("newest"),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    cart_count, fav_count = nav(user, db)

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

    products_list = query.all()
    categories = db.query(Category).all()
    fav_ids = {f.product_id for f in db.query(Favorite).filter_by(user_id=user.id).all()} if user else set()

    return templates.TemplateResponse("products.html", {
        "request": request,
        "user": user,
        "products": products_list,
        "categories": categories,
        "cart_count": cart_count,
        "fav_count": fav_count,
        "fav_ids": fav_ids,
        "q": q or "",
        "selected_category": category_id,
        "min_price": min_price or "",
        "max_price": max_price or "",
        "sort": sort,
    })


@router.get("/{product_id}", response_class=HTMLResponse)
async def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    cart_count, fav_count = nav(user, db)

    product = db.query(Product).filter_by(id=product_id, status="approved").first()
    if not product:
        return RedirectResponse("/products", status_code=302)

    is_favorite = bool(
        user and db.query(Favorite).filter_by(user_id=user.id, product_id=product_id).first()
    )
    related = (
        db.query(Product)
        .filter(Product.category_id == product.category_id, Product.id != product_id, Product.status == "approved")
        .limit(4)
        .all()
    )

    return templates.TemplateResponse("product_detail.html", {
        "request": request,
        "user": user,
        "product": product,
        "is_favorite": is_favorite,
        "related": related,
        "cart_count": cart_count,
        "fav_count": fav_count,
    })

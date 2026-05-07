from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os, uuid

from app.database import get_db
from app.models import Product, Category, CartItem, Favorite
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = "app/static/uploads"


def nav(user, db):
    if not user:
        return 0, 0
    return (
        db.query(CartItem).filter_by(user_id=user.id).count(),
        db.query(Favorite).filter_by(user_id=user.id).count(),
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    if user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)
    cart_count, fav_count = nav(user, db)
    my_products = db.query(Product).filter_by(seller_id=user.id).order_by(Product.created_at.desc()).all()
    return templates.TemplateResponse("seller/dashboard.html", {
        "request": request,
        "user": user,
        "products": my_products,
        "cart_count": cart_count,
        "fav_count": fav_count,
    })


@router.get("/add", response_class=HTMLResponse)
async def add_product_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)
    cart_count, fav_count = nav(user, db)
    categories = db.query(Category).all()
    return templates.TemplateResponse("seller/add_product.html", {
        "request": request,
        "user": user,
        "categories": categories,
        "cart_count": cart_count,
        "fav_count": fav_count,
        "error": None,
    })


@router.post("/add", response_class=HTMLResponse)
async def add_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    category_id: Optional[int] = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user or user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)

    img_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            filename = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(UPLOAD_DIR, filename)
            with open(path, "wb") as f:
                f.write(await image.read())
            img_url = f"/static/uploads/{filename}"

    product = Product(
        name=name,
        description=description,
        price=price,
        category_id=category_id or None,
        seller_id=user.id,
        img_url=img_url,
        status="pending",
    )
    db.add(product)
    db.commit()
    return RedirectResponse("/seller/dashboard", status_code=302)


@router.get("/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_page(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if not product:
        return RedirectResponse("/seller/dashboard", status_code=302)
    categories = db.query(Category).all()
    cart_count, fav_count = nav(user, db)
    return templates.TemplateResponse("seller/add_product.html", {
        "request": request,
        "user": user,
        "product": product,
        "categories": categories,
        "cart_count": cart_count,
        "fav_count": fav_count,
        "error": None,
    })


@router.post("/edit/{product_id}", response_class=HTMLResponse)
async def edit_product(
    product_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    category_id: Optional[int] = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user or user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if not product:
        return RedirectResponse("/seller/dashboard", status_code=302)

    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            filename = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(UPLOAD_DIR, filename)
            with open(path, "wb") as f:
                f.write(await image.read())
            product.img_url = f"/static/uploads/{filename}"

    product.name = name
    product.description = description
    product.price = price
    product.category_id = category_id or None
    product.status = "pending"
    db.commit()
    return RedirectResponse("/seller/dashboard", status_code=302)


@router.post("/delete/{product_id}")
async def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role not in ("seller", "admin"):
        return RedirectResponse("/become-seller", status_code=302)
    product = db.query(Product).filter_by(id=product_id, seller_id=user.id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/seller/dashboard", status_code=302)

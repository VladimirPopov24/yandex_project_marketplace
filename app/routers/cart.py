from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, CartItem, Favorite, Order
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def cart_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    total = sum(i.product.price * i.quantity for i in items)
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return templates.TemplateResponse("cart.html", {
        "request": request,
        "user": user,
        "items": items,
        "total": total,
        "cart_count": len(items),
        "fav_count": fav_count,
        "success": None,
    })


@router.post("/add/{product_id}")
async def add_to_cart(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    product = db.query(Product).filter_by(id=product_id, status="approved").first()
    if not product:
        return JSONResponse({"error": "not found"}, status_code=404)
    existing = db.query(CartItem).filter_by(user_id=user.id, product_id=product_id).first()
    if existing:
        existing.quantity += 1
    else:
        db.add(CartItem(user_id=user.id, product_id=product_id, quantity=1))
    db.commit()
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count()
    return JSONResponse({"success": True, "cart_count": cart_count})


@router.post("/update/{item_id}")
async def update_cart(
    item_id: int,
    request: Request,
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    item = db.query(CartItem).filter_by(id=item_id, user_id=user.id).first()
    if item:
        if quantity < 1:
            db.delete(item)
        else:
            item.quantity = quantity
        db.commit()
    return RedirectResponse("/cart", status_code=302)


@router.post("/remove/{item_id}")
async def remove_from_cart(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    item = db.query(CartItem).filter_by(id=item_id, user_id=user.id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/cart", status_code=302)


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    if not items:
        return RedirectResponse("/cart", status_code=302)
    total = sum(i.product.price * i.quantity for i in items)
    cart_count = len(items)
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return templates.TemplateResponse("checkout.html", {
        "request": request, "user": user, "items": items,
        "total": total, "cart_count": cart_count, "fav_count": fav_count,
    })


@router.post("/checkout")
async def checkout(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    payment: str = Form(...),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    items = db.query(CartItem).filter_by(user_id=user.id).all()
    if not items:
        return RedirectResponse("/cart", status_code=302)
    total = sum(i.product.price * i.quantity for i in items)
    order = Order(user_id=user.id, total=total, status="new")
    db.add(order)
    db.flush()
    for item in items:
        db.delete(item)
    db.commit()
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return templates.TemplateResponse("order_success.html", {
        "request": request, "user": user,
        "order_id": order.id, "total": total,
        "full_name": full_name, "address": address,
        "payment": payment, "cart_count": 0, "fav_count": fav_count,
    })

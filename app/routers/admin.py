from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, Product, Category, Order
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_admin(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        return None
    return user


@router.get("", response_class=HTMLResponse)
async def admin_root(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse("/admin/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    total_categories = db.query(Category).count()
    pending = db.query(Product).filter_by(status="pending").all()
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "total_users": total_users,
        "total_products": total_products,
        "total_categories": total_categories,
        "pending": pending,
        "recent_users": recent_users,
        "cart_count": 0,
        "fav_count": 0,
    })


# ── Products moderation ──────────────────────────────────────────────────────

@router.get("/products", response_class=HTMLResponse)
async def admin_products(
    request: Request,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

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

    return templates.TemplateResponse("admin/products.html", {
        "request": request,
        "user": user,
        "products": items,
        "status": status or "all",
        "counts": counts,
        "cart_count": 0,
        "fav_count": 0,
    })


@router.post("/products/{product_id}/approve")
async def approve_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        p.status = "approved"
        db.commit()
    return RedirectResponse("/admin/products?status=pending", status_code=302)


@router.post("/products/{product_id}/reject")
async def reject_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        p.status = "rejected"
        db.commit()
    return RedirectResponse("/admin/products?status=pending", status_code=302)


@router.post("/products/{product_id}/delete")
async def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    p = db.query(Product).filter_by(id=product_id).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/admin/products", status_code=302)


# ── Users management ─────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    query = db.query(User)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))
    if role and role != "all":
        query = query.filter(User.role == role)
    users = query.order_by(User.created_at.desc()).all()

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": user,
        "users": users,
        "q": q or "",
        "role": role or "all",
        "cart_count": 0,
        "fav_count": 0,
    })


@router.post("/users/{user_id}/toggle-block")
async def toggle_block(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = require_admin(request, db)
    if not admin:
        return RedirectResponse("/auth/login", status_code=302)
    target = db.query(User).filter_by(id=user_id).first()
    if target and target.role != "admin":
        target.is_blocked = not target.is_blocked
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/change-role")
async def change_role(
    user_id: int,
    request: Request,
    new_role: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = require_admin(request, db)
    if not admin:
        return RedirectResponse("/auth/login", status_code=302)
    target = db.query(User).filter_by(id=user_id).first()
    if target and target.id != admin.id and new_role in ("buyer", "seller"):
        target.role = new_role
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)


# ── Categories management ────────────────────────────────────────────────────

@router.get("/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    from sqlalchemy import func
    cats = (
        db.query(Category, func.count(Product.id).label("cnt"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
        .all()
    )

    return templates.TemplateResponse("admin/categories.html", {
        "request": request,
        "user": user,
        "categories": cats,
        "cart_count": 0,
        "fav_count": 0,
        "error": None,
    })


@router.post("/categories/add")
async def add_category(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    name = name.strip()
    if name and not db.query(Category).filter_by(name=name).first():
        db.add(Category(name=name))
        db.commit()
    return RedirectResponse("/admin/categories", status_code=302)


@router.post("/categories/{cat_id}/delete")
async def delete_category(cat_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_admin(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    cat = db.query(Category).filter_by(id=cat_id).first()
    if cat:
        db.query(Product).filter_by(category_id=cat_id).update({"category_id": None})
        db.delete(cat)
        db.commit()
    return RedirectResponse("/admin/categories", status_code=302)

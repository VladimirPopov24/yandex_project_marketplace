from fastapi import APIRouter, Request, Depends, Form, Query
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, CartItem, Favorite
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def nav(user, db):
    if not user:
        return 0, 0
    return (
        db.query(CartItem).filter_by(user_id=user.id).count(),
        db.query(Favorite).filter_by(user_id=user.id).count(),
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request, "user": None, "cart_count": 0, "fav_count": 0, "error": None
    })


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    ctx = {"request": request, "user": None, "cart_count": 0, "fav_count": 0}
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {**ctx, "error": "Неверный логин или пароль"})
    if user.is_blocked:
        return templates.TemplateResponse("login.html", {**ctx, "error": "Аккаунт заблокирован"})
    token = create_access_token(user.id)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=86400)
    return resp


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, seller: Optional[int] = Query(None), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("register.html", {
        "request": request, "user": None, "cart_count": 0, "fav_count": 0,
        "error": None, "seller_mode": bool(seller),
    })


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    seller_mode: int = Form(0),
    db: Session = Depends(get_db),
):
    ctx = {"request": request, "user": None, "cart_count": 0, "fav_count": 0, "seller_mode": bool(seller_mode)}
    if password != confirm_password:
        return templates.TemplateResponse("register.html", {**ctx, "error": "Пароли не совпадают"})
    if len(username) < 3:
        return templates.TemplateResponse("register.html", {**ctx, "error": "Логин минимум 3 символа"})
    if len(password) < 4:
        return templates.TemplateResponse("register.html", {**ctx, "error": "Пароль минимум 4 символа"})
    if db.query(User).filter_by(username=username).first():
        return templates.TemplateResponse("register.html", {**ctx, "error": "Такой логин уже занят"})

    role = "seller" if seller_mode else "buyer"
    new_user = User(username=username, password_hash=get_password_hash(password), role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.id)
    redirect_to = "/seller/dashboard" if role == "seller" else "/"
    resp = RedirectResponse(redirect_to, status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=86400)
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("access_token")
    return resp

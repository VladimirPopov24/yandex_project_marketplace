from flask import Blueprint, render_template, request, redirect, make_response
from app.database import get_db
from app.models import User
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():
    db = get_db()
    user = get_current_user(db)
    if user:
        return redirect("/")
    return render_template("login.html", user=None, cart_count=0, fav_count=0, error=None)


@auth_bp.route("/login", methods=["POST"])
def login():
    db = get_db()
    ctx = {"user": None, "cart_count": 0, "fav_count": 0}
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return render_template("login.html", **ctx, error="Неверный логин или пароль")
    if user.is_blocked:
        return render_template("login.html", **ctx, error="Аккаунт заблокирован")
    token = create_access_token(user.id)
    resp = make_response(redirect("/"))
    resp.set_cookie("access_token", token, httponly=True, max_age=86400)
    return resp


@auth_bp.route("/register", methods=["GET"])
def register_page():
    db = get_db()
    user = get_current_user(db)
    if user:
        return redirect("/")
    seller = request.args.get("seller")
    return render_template("register.html", user=None, cart_count=0, fav_count=0,
                           error=None, seller_mode=bool(seller))


@auth_bp.route("/register", methods=["POST"])
def register():
    db = get_db()
    seller_mode = bool(int(request.form.get("seller_mode", 0)))
    ctx = {"user": None, "cart_count": 0, "fav_count": 0, "seller_mode": seller_mode}
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    if password != confirm_password:
        return render_template("register.html", **ctx, error="Пароли не совпадают")
    if len(username) < 3:
        return render_template("register.html", **ctx, error="Логин минимум 3 символа")
    if len(password) < 4:
        return render_template("register.html", **ctx, error="Пароль минимум 4 символа")
    if db.query(User).filter_by(username=username).first():
        return render_template("register.html", **ctx, error="Такой логин уже занят")
    role = "seller" if seller_mode else "buyer"
    new_user = User(username=username, password_hash=get_password_hash(password), role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token(new_user.id)
    redirect_to = "/seller/dashboard" if role == "seller" else "/"
    resp = make_response(redirect(redirect_to))
    resp.set_cookie("access_token", token, httponly=True, max_age=86400)
    return resp


@auth_bp.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("access_token")
    return resp

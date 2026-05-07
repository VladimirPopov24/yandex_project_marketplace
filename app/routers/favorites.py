from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, CartItem, Favorite
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def favorites_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    favs = db.query(Favorite).filter_by(user_id=user.id).all()
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count()
    return templates.TemplateResponse("favorites.html", {
        "request": request,
        "user": user,
        "favorites": favs,
        "cart_count": cart_count,
        "fav_count": len(favs),
    })


@router.post("/toggle/{product_id}")
async def toggle_favorite(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    existing = db.query(Favorite).filter_by(user_id=user.id, product_id=product_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    else:
        product = db.query(Product).filter_by(id=product_id, status="approved").first()
        if not product:
            return JSONResponse({"error": "not found"}, status_code=404)
        db.add(Favorite(user_id=user.id, product_id=product_id))
        db.commit()
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    is_fav = not existing
    return JSONResponse({"success": True, "is_favorite": is_fav, "fav_count": fav_count})

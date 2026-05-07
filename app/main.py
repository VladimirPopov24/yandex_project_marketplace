import os
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import engine, get_db
from app.models import Base, User, Category, Product, CartItem, Favorite
from app.auth import get_password_hash, get_current_user
from app.routers import auth, products, cart, favorites, seller, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Modex Marketplace", redirect_slashes=False)

os.makedirs("app/static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router, prefix="/auth")
app.include_router(products.router, prefix="/products")
app.include_router(cart.router, prefix="/cart")
app.include_router(favorites.router, prefix="/favorites")
app.include_router(seller.router, prefix="/seller")
app.include_router(admin.router, prefix="/admin")

# ── Seed data ─────────────────────────────────────────────────────────────────
# Unsplash URL helper
def u(photo_id: str) -> str:
    if photo_id.startswith("http"):
        return photo_id
    return f"https://images.unsplash.com/photo-{photo_id}?w=500&h=370&fit=crop&auto=format&q=80"


CATEGORIES = [
    "Смартфоны",
    "Электроника",
    "Компьютеры",
    "Одежда",
    "Обувь",
    "Спорт и фитнес",
    "Красота и здоровье",
    "Дом и сад",
    "Книги",
    "Игрушки",
    "Животные",
    "Музыка",
    "Авто",
    "Детские товары",
]

# (name, description, price, category_name, unsplash_photo_id)
SAMPLE_PRODUCTS = [
    # Смартфоны
    ("iPhone 15 Pro 256 ГБ",
     "Смартфон Apple с чипом A17 Pro, камерой 48 Мп и корпусом из титана. Цвет: Чёрный титан.",
     89990, "Смартфоны", "1511707171634-5f897ff02aa9"),

    ("Samsung Galaxy S24 Ultra",
     "Флагман Samsung со встроенным стилусом S Pen, AI-функциями и камерой 200 Мп.",
     99990, "Смартфоны", "1705585174953-9b2aa8afc174"),

    ("Xiaomi 14 Pro",
     "Мощный смартфон с камерой Leica, экраном 120 Гц и зарядкой 120 Вт.",
     64990, "Смартфоны", "https://static.insales-cdn.com/images/products/1/5958/960239430/Redmi_Note_14_Pro_4G_black.png"),

    ("Google Pixel 8",
     "Чистый Android с лучшей AI-камерой на рынке и 7 лет обновлений.",
     54990, "Смартфоны", "1706412703794-d944cd3625b3"),

    # Электроника
    ("Samsung QLED 55\" 4K",
     "Телевизор с квантовыми точками, HDR10+ и Smart TV на Tizen. Диагональ 55 дюймов.",
     54990, "Электроника", "1593359677879-a4bb92f829d1"),

    ("AirPods Pro 2",
     "Беспроводные наушники с активным шумоподавлением, прозрачностью и Adaptive Audio.",
     19990, "Электроника", "1600294037681-c80b4cb5b434"),

    ("Яндекс Станция Макс",
     "Умная колонка с Алисой, Hi-Fi звуком, встроенным экраном и умным домом.",
     14990, "Электроника", "1543512214-318c7553f230"),

    ("Робот-пылесос Xiaomi S10+",
     "Лазерная навигация LiDAR, всасывание 4000 Па, мытьё пола, работа до 3 часов.",
     34990, "Электроника", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQehXAY_PkxE15AhnJhpM_OAjZWkbVajzAgQQ&s"),

    ("Фотоаппарат Sony Alpha A7 IV",
     "Полнокадровая беззеркальная камера 33 Мп, 4K видео, стабилизация 5-осевая.",
     149990, "Электроника", "1516035069371-29a1b244cc32"),

    ("Philips Hue Starter Kit",
     "Умные лампочки с 16 млн цветов, управление через приложение и голосом.",
     8990, "Электроника", "https://m.chodo.ru/userfiles/images/photogalleries/14245_1/1645451220_2_727892-1809x1328.jpeg"),

    # Компьютеры
    ("MacBook Air M2 13\"",
     "Ноутбук Apple с чипом M2, 8 ГБ RAM, SSD 256 ГБ. Автономность до 18 часов.",
     99990, "Компьютеры", "1496181133206-80ce9b88a853"),

    ("Lenovo IdeaPad 5i",
     "15.6\", Intel Core i5-12450H, 16 ГБ RAM, SSD 512 ГБ, FullHD IPS-дисплей.",
     52990, "Компьютеры", "1517336714731-489689fd1ca8"),

    ("Logitech MX Master 3S",
     "Беспроводная мышь с тихими кнопками, колесом MagSpeed и подключением до 3 устройств.",
     7990, "Компьютеры", "1527443224154-c4a3942d3acf"),

    ("Клавиатура Keychron K2",
     "Механическая компактная клавиатура, RGB, Bluetooth + USB-C, переключатели Gateron.",
     8990, "Компьютеры", "1587829741301-dc798b83add3"),

    ("Монитор Dell UltraSharp 27\"",
     "IPS-панель 2560×1440, 60 Гц, USB-C 90W, идеальная цветопередача для дизайнеров.",
     39990, "Компьютеры", "1585771724684-38269d6639fd"),

    # Одежда
    ("Джинсы Levi's 501 Original",
     "Классические прямые джинсы из тяжёлого денима. Крой regular fit. Размер 32×32.",
     5490, "Одежда", "1542272604-787c3835535d"),

    ("Худи Champion Reverse Weave",
     "Тяжёлый хлопковый флис, вышитый логотип, кенгуру-карман. Цвет: Oxford Grey.",
     4990, "Одежда", "1509631179647-0177331693ae"),

    ("Футболка Uniqlo AIRism",
     "Ультралёгкая быстросохнущая футболка. Идеальна для жаркой погоды.",
     1490, "Одежда", "1521572163474-6864f9cf17ab"),

    ("Кожаная куртка косуха",
     "Натуральная кожа, подкладка из вискозы, металлическая фурнитура. Унисекс.",
     12990, "Одежда", "1551028719-00167b16eac5"),

    ("Платье Zara льняное",
     "Льняное платье-рубашка миди, свободный силуэт. Цвет: натуральный экрю.",
     3990, "Одежда", "1610030469983-98e550d6193c"),

    # Обувь
    ("Nike Air Max 270",
     "Кроссовки с крупнейшей подушкой Air в пятке для максимальной амортизации.",
     8990, "Обувь", "1542291026-7eec264c27ff"),

    ("Adidas Ultraboost 23",
     "Беговые кроссовки с технологией Boost и верхом из Primeknit+. Для длинных дистанций.",
     11990, "Обувь", "https://thumblr.uniid.it/product/341531/410ce0a5053a.jpg?width=3840&format=webp&q=75"),

    ("Vans Old Skool",
     "Классические низкие кеды с фирменной полосой. Верх из замши и канваса.",
     4990, "Обувь", "1560769629-975ec94e6a86"),

    ("Timberland Premium 6\"",
     "Водонепроницаемые ботинки из нубука, подошва из EVA, зимняя подкладка.",
     14990, "Обувь", "https://bootwood.com/upload/iblock/9b3/j18hk0wk4ty90p0c0tpk5q0bdb9jprev/69a17a168393e.jpg"),

    # Спорт и фитнес
    ("Гантели разборные 2×10 кг",
     "Хромированные диски, прорезиненные накладки, замки-гайки в комплекте.",
     2990, "Спорт и фитнес", "1571019614242-c5c5dee9f50b"),

    ("Коврик для йоги Manduka PRO",
     "6 мм, нескользящее покрытие, вес 3.2 кг, пожизненная гарантия от производителя.",
     6990, "Спорт и фитнес", "1571019613454-1cb2f99b2d8b"),

    ("Горный велосипед Trek Marlin 5",
     "Алюминиевая рама, 29\" колёса, 24 скорости Shimano, гидравлические тормоза.",
     54990, "Спорт и фитнес", "1485965120184-e220f721d03e"),

    ("Скакалка со счётчиком",
     "Стальной трос, ручки с подшипниками, счётчик прыжков и калорий.",
     890, "Спорт и фитнес", "1553062407-98eeb64c6a62"),

    # Красота и здоровье
    ("Парфюм Chanel N°5 EDP 50 мл",
     "Классический аромат с нотами розы, жасмина и сандала. Оригинал.",
     12990, "Красота и здоровье", "1556228453-efd6c1ff04f6"),

    ("Набор Drunk Elephant Basic Moisturizing",
     "Дневной и ночной крем, сыворотка с витамином C, SPF-защита. Без ароматизаторов.",
     8490, "Красота и здоровье", "1556228720-195a672e8a03"),

    ("Электробритва Braun Series 9 Pro",
     "5 режимов бритья, умная вибрация, автоочистка, аккумулятор 60 мин.",
     14990, "Красота и здоровье", "1516571748831-5d81767b788d"),

    # Дом и сад
    ("Набор садовых инструментов Fiskars",
     "Лопата, грабли, совок, рыхлитель — нержавеющая сталь, удобные рукояти.",
     2990, "Дом и сад", "1416879595882-3373a0480b5b"),

    ("Фикус Бенджамина 100 см",
     "Неприхотливое комнатное дерево в горшке, высота 100 см. Очищает воздух.",
     2490, "Дом и сад", "1485955900006-10f4d324d411"),

    ("Диффузор Muuto Base",
     "Скандинавский керамический диффузор с набором эфирных масел на 30 дней.",
     3990, "Дом и сад", "1523275335684-37898b6baf30"),

    # Книги
    ("Python. Марк Лутц",
     "Исчерпывающее руководство по Python — от основ до продвинутых тем. 5-е издание.",
     1490, "Книги", "1544716278-ca5e3f4abd8c"),

    ("Чистый код. Роберт Мартин",
     "Создание, анализ и рефакторинг кода — настольная книга каждого разработчика.",
     1190, "Книги", "1532012197267-da84d127e765"),

    ("Атомные привычки. Джеймс Клир",
     "Проверенный способ приобретать хорошие привычки и избавляться от плохих.",
     890, "Книги", "1481627834876-b7833e8f5570"),

    # Игрушки
    ("LEGO Technic BMW M 1000 RR",
     "Мотоцикл из 1920 деталей с подвижными поршнями двигателя, возраст 18+.",
     8990, "Игрушки", "1558618666-fcd25c85cd64"),

    ("Монополия Classic",
     "Настольная игра для всей семьи, 2–8 игроков, новое оформление, 60+ карточек.",
     1990, "Игрушки", "1608889825103-eb5ed706fc64"),

    # Животные
    ("Корм Royal Canin для кошек 2 кг",
     "Сухой корм для взрослых кошек, поддержка веса, здоровье зубов и шерсти.",
     1290, "Животные", "1517423440428-a5a00ad493e8"),

    ("Поводок-рулетка Flexi New Classic",
     "5 метров, нагрузка до 25 кг, кнопка стоп, карабин из нержавеющей стали.",
     1490, "Животные", "1587300003388-59208cc962cb"),

    # Музыка
    ("Акустическая гитара Yamaha F310",
     "Дредноут, верхняя дека из ели, гриф из нато, идеальна для начинающих.",
     9990, "Музыка", "1510915361894-db8b60106cb1"),

    ("Наушники Sony WH-1000XM5",
     "Лучшее шумоподавление в классе, 30 ч автономность, Hi-Res Audio.",
     29990, "Музыка", "1505740420928-5e560c06d30e"),

    # Авто
    ("Видеорегистратор Xiaomi 70mai A800S",
     "4K запись, угол 140°, ночное зрение, GPS, встроенный Wi-Fi, голосовое управление.",
     9990, "Авто", "1502877338535-766e1452684a"),

    ("Автомобильный пылесос Baseus",
     "120 Вт, 6000 Па, HEPA-фильтр, провод 5 м, набор насадок в комплекте.",
     2490, "Авто", "1527613426441-4da17471b66d"),

    # Детские товары
    ("Конструктор LEGO DUPLO Зоопарк",
     "142 детали, 8 фигурок животных, подходит детям от 2 лет, развивает моторику.",
     3490, "Детские товары", "1558618666-fcd25c85cd64"),

    ("Самокат Micro Maxi Deluxe",
     "Регулируемый руль 72–95 см, нагрузка до 50 кг, силиконовые колёса, тихий ход.",
     6990, "Детские товары", "1515886657613-9f3515b0c78f"),
]


def seed(db: Session):
    # Admin
    if not db.query(User).filter_by(username="admin").first():
        db.add(User(username="admin", password_hash=get_password_hash("admin123"), role="admin"))
        db.commit()

    # Categories
    for name in CATEGORIES:
        if not db.query(Category).filter_by(name=name).first():
            db.add(Category(name=name))
    db.commit()

    # Products — reseed if empty or has old picsum URLs
    first = db.query(Product).filter(Product.seller_id == None).first()
    needs_reseed = first is None or "picsum" in (first.img_url or "")

    if needs_reseed:
        db.query(Product).filter(Product.seller_id == None).delete(synchronize_session=False)
        db.commit()
        cats = {c.name: c for c in db.query(Category).all()}
        for name, desc, price, cat_name, photo_id in SAMPLE_PRODUCTS:
            cat = cats.get(cat_name)
            db.add(Product(
                name=name,
                description=desc,
                price=price,
                category_id=cat.id if cat else None,
                img_url=u(photo_id),
                status="approved",
            ))
        db.commit()
    else:
        # Update URLs for existing sample products to fix broken photo IDs
        cats = {c.name: c for c in db.query(Category).all()}
        url_map = {name: u(photo_id) for name, _, _, _, photo_id in SAMPLE_PRODUCTS}
        for name, desc, price, cat_name, photo_id in SAMPLE_PRODUCTS:
            correct_url = u(photo_id)
            db.query(Product).filter(
                Product.seller_id == None,
                Product.name == name,
                Product.img_url != correct_url,
            ).update({"img_url": correct_url}, synchronize_session=False)
        db.commit()


@app.on_event("startup")
def startup():
    db = next(get_db())
    seed(db)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    featured = db.query(Product).filter_by(status="approved").limit(8).all()
    categories = db.query(Category).all()
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count() if user else 0
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count() if user else 0
    fav_ids = {f.product_id for f in db.query(Favorite).filter_by(user_id=user.id).all()} if user else set()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "featured": featured,
        "categories": categories,
        "cart_count": cart_count,
        "fav_count": fav_count,
        "fav_ids": fav_ids,
    })


@app.get("/become-seller", response_class=HTMLResponse)
async def become_seller_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count() if user else 0
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count() if user else 0
    if user and user.role in ("seller", "admin"):
        return RedirectResponse("/seller/dashboard", status_code=302)
    return templates.TemplateResponse("become_seller.html", {
        "request": request,
        "user": user,
        "cart_count": cart_count,
        "fav_count": fav_count,
    })


@app.post("/become-seller")
async def become_seller(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/register?seller=1", status_code=302)
    user.role = "seller"
    db.commit()
    return RedirectResponse("/seller/dashboard", status_code=302)


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count()
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count()
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "cart_count": cart_count,
        "fav_count": fav_count,
    })

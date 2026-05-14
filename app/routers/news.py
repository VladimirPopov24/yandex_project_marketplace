import re
import feedparser
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from app.database import get_db
from app.auth import get_current_user
from app.models import CartItem, Favorite, NewsSource, NewsArticle

news_bp = Blueprint("news", __name__)

NEWS_SOURCES = [
    {"name": "Habr — Железо", "url": "https://habr.com", "rss_url": "https://habr.com/ru/rss/hub/hardware/articles/", "category": "Железо"},
    {"name": "Habr — IT", "url": "https://habr.com", "rss_url": "https://habr.com/ru/rss/hub/it/articles/", "category": "IT"},
    {"name": "Habr — Гаджеты", "url": "https://habr.com", "rss_url": "https://habr.com/ru/rss/hub/gadgets/articles/", "category": "Гаджеты"},
    {"name": "3DNews", "url": "https://3dnews.ru", "rss_url": "https://3dnews.ru/news/rss/", "category": "Техника"},
    {"name": "iXBT", "url": "https://ixbt.com", "rss_url": "https://www.ixbt.com/export/news.rss", "category": "Техника"},
    {"name": "CNews", "url": "https://cnews.ru", "rss_url": "https://www.cnews.ru/inc/rss/news.xml", "category": "IT"},
    {"name": "Overclockers", "url": "https://overclockers.ru", "rss_url": "https://overclockers.ru/rss/news", "category": "Железо"},
    {"name": "Ferra", "url": "https://ferra.ru", "rss_url": "https://www.ferra.ru/rss/news.xml", "category": "Гаджеты"},
]

NEWS_CATEGORIES = ["Все", "IT", "Железо", "Гаджеты", "Техника"]


def _extract_image(entry):
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            if m.get("url"):
                return m["url"]
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", "") and enc.get("href"):
                return enc["href"]
    html = ""
    if hasattr(entry, "content") and entry.content:
        html = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        html = entry.summary or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    return m.group(1) if m else None


def _clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6])
            except Exception:
                pass
    return datetime.utcnow()


def seed_news_sources(db):
    for s in NEWS_SOURCES:
        if not db.query(NewsSource).filter_by(rss_url=s["rss_url"]).first():
            db.add(NewsSource(**s))
    db.commit()


def fetch_source(source: NewsSource, db) -> int:
    try:
        feed = feedparser.parse(source.rss_url)
        count = 0
        for entry in feed.entries:
            url = entry.get("link") or entry.get("id")
            if not url:
                continue
            if db.query(NewsArticle).filter_by(url=url).first():
                continue
            raw_summary = (entry.get("content") or [{}])[0].get("value") or entry.get("summary", "")
            db.add(NewsArticle(
                title=entry.get("title", "Без заголовка")[:500],
                summary=_clean_html(raw_summary),
                url=url,
                image_url=_extract_image(entry),
                published_at=_parse_date(entry),
                source_id=source.id,
            ))
            count += 1
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        print(f"[news] ERROR {source.name}: {e}")
        return 0


def fetch_all_news(db) -> int:
    total = 0
    for src in db.query(NewsSource).all():
        n = fetch_source(src, db)
        if n:
            print(f"[news] {src.name}: +{n}")
        total += n
    print(f"[news] done, new articles: {total}")
    return total


@news_bp.route("/news", methods=["GET"])
def news_page():
    db = get_db()
    user = get_current_user(db)
    cart_count = db.query(CartItem).filter_by(user_id=user.id).count() if user else 0
    fav_count = db.query(Favorite).filter_by(user_id=user.id).count() if user else 0
    category = request.args.get("category", "Все")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 18
    q = db.query(NewsArticle).join(NewsSource)
    if category and category != "Все":
        q = q.filter(NewsSource.category == category)
    q = q.order_by(NewsArticle.published_at.desc())
    total = q.count()
    articles = q.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page)
    return render_template("news.html", user=user, cart_count=cart_count, fav_count=fav_count,
                           articles=articles, categories=NEWS_CATEGORIES, current_category=category,
                           page=page, pages=pages, total=total)


@news_bp.route("/news/refresh", methods=["POST"])
def news_refresh():
    db = get_db()
    total = fetch_all_news(db)
    return jsonify({"added": total, "total": db.query(NewsArticle).count()})

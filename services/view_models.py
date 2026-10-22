"""Kesh uchun yengil (pickle-safe) ko'rinish modellari.

SQLAlchemy ``Pagination`` va ORM obyektlari ichida ``Session`` bo'ladi,
shuning uchun ularni Redis'ga pickle qilib bo'lmaydi: ``cache_set`` har
safar xato berib, jimgina in-memory rejimga qaytardi. Natijada Redis
yoqilgan production'da kesh workerlar o'rtasida bo'linmasdi.

Bu modul keshga faqat oddiy Python qiymatlarini (dict/list/datetime)
yozadi, shablonlarga esa attribute-access bilan ishlaydigan
``SimpleNamespace`` uzatadi. Shu tufayli Redis'dagi kesh haqiqatan
ishlaydi va ko'p workerli deploy'da ham umumiy bo'ladi.
"""
from types import SimpleNamespace


def _page_meta(pagination):
    """Pagination obyektidan faqat serializable metama'lumotni oladi."""
    return {
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page,
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "prev_num": pagination.prev_num,
        "next_num": pagination.next_num,
    }


def empty_page(per_page):
    """Baza xatosi yoki bo'sh natija uchun xavfsiz sahifa payload'i."""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "pages": 1,
        "per_page": per_page,
        "has_prev": False,
        "has_next": False,
        "prev_num": None,
        "next_num": None,
    }


def post_card(post):
    """``Post`` modelidan ro'yxat sahifasida kerakli maydonlar."""
    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "content": post.content or "",
        "category": post.category,
        "image_url": post.image_url,
        "views": post.views or 0,
        "reading_time": post.reading_time,
        "created_at": post.created_at,
    }


def portfolio_card(item, resolved_img):
    """Portfolio kartochkasi uchun maydonlar (ORM obyektisiz)."""
    return {
        "id": item.id,
        "title": item.title,
        "slug": item.slug,
        "description": item.description,
        "category": item.category,
        "emoji": item.emoji,
        "technologies": item.technologies or "",
        "link": item.link,
        "image_url": item.image_url,
        "is_featured": bool(item.is_featured),
        "client_name": item.client_name,
        "problem": item.problem,
        "result": item.result,
        "video_url": item.video_url,
        "gallery_images": item.gallery_images,
        "_resolved_img": resolved_img,
    }


def portfolio_page(pagination, resolve_image):
    """Portfolio sahifasining to'liq kesh payload'i."""
    items = []
    json_items = []
    for item in pagination.items:
        items.append(portfolio_card(item, resolve_image(item)))
        # Meta/JS uchun JSON ham keshga tushadi — model obyekti emas, dict.
        json_items.append(item.to_dict())

    payload = _page_meta(pagination)
    payload["items"] = items
    payload["json_items"] = json_items
    return payload


def blog_page(pagination, popular_posts):
    """Blog sahifasining to'liq kesh payload'i."""
    payload = _page_meta(pagination)
    payload["items"] = [post_card(post) for post in pagination.items]
    payload["popular"] = [post_card(post) for post in popular_posts]
    return payload


def page_namespace(payload):
    """Keshdan olingan dict'ni shablon kutgan attribute-obyektga aylantiradi."""
    page = {
        key: value
        for key, value in payload.items()
        if key not in ("items", "json_items", "popular")
    }
    page["items"] = item_namespaces(payload.get("items", []))
    return SimpleNamespace(**page)


def item_namespaces(items):
    """Dict ro'yxatini Jinja uchun attribute-obyektlar ro'yxatiga aylantiradi."""
    return [SimpleNamespace(**item) for item in items]

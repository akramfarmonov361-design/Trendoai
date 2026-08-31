import re
from datetime import datetime
from flask import current_app, redirect, render_template, request, url_for, Response
import markdown2
from xml.sax.saxutils import escape as xml_escape

from extensions import db
from models.post import Post
from routes.web._blueprint import web_bp
from config import POSTS_PER_PAGE, SITE_DESCRIPTION, SITE_NAME, SITE_URL
from services.cache_service import cache_get, cache_set

@web_bp.route('/blog')
def blog():
    """Blog sahifasi — barcha postlar ro'yxati"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)

    cache_key = f"blog:{page}:{category or ''}"
    is_testing = bool(current_app.config.get('TESTING'))
    cached = cache_get(cache_key, is_testing=is_testing)

    if cached is not None:
        pagination, popular_posts = cached
    else:
        query = Post.query.filter_by(is_published=True)
        if category:
            query = query.filter_by(category=category)

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=POSTS_PER_PAGE, error_out=False
        )
        popular_posts = Post.query.filter_by(is_published=True).order_by(
            Post.views.desc()
        ).limit(5).all()

        cache_set(cache_key, (pagination, popular_posts), ttl=60, is_testing=is_testing)

    return render_template('index.html',
                           posts=pagination.items,
                           pagination=pagination,
                           popular_posts=popular_posts)

@web_bp.route('/post/<int:post_id>')
def post(post_id):
    """Legacy ID orqali post sahifasi - slug ga 301 doimiy redirect"""
    p = Post.query.get_or_404(post_id)
    if p.slug and not p.slug.startswith('json'):
        return redirect(url_for('web.post_by_slug', slug=p.slug), code=301)
    return redirect(url_for('web.blog'), code=301)

@web_bp.route('/blog/<slug>')
def post_by_slug(slug):
    """Slug orqali post sahifasi (SEO-friendly)"""
    # 301 redirect for corrupted legacy json-* URLs from old crawlers
    clean_slug = (slug or '').strip().lower()
    if clean_slug.startswith('json') or '```' in clean_slug:
        return redirect(url_for('web.blog'), code=301)

    p = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    p.views = (p.views or 0) + 1
    db.session.commit()

    related_posts = Post.query.filter(
        Post.id != p.id,
        Post.category == p.category,
        Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(3).all()

    return render_template('post.html', post=p, related_posts=related_posts)

@web_bp.route('/rss')
def rss_feed():
    """Blog RSS 2.0 feed"""
    posts = Post.query.filter(
        Post.is_published == True,
        Post.slug.isnot(None)
    ).order_by(Post.created_at.desc()).limit(30).all()

    items = []
    for p in posts:
        link = f"{SITE_URL}/blog/{p.slug}"
        plain = re.sub(r'<[^>]+>', '', markdown2.markdown(p.content or ''))
        plain = re.sub(r'\s+', ' ', plain).strip()[:300]
        pub_date = (p.created_at or datetime.utcnow()).strftime('%a, %d %b %Y %H:%M:%S +0000')

        item = (
            "  <item>\n"
            f"    <title>{xml_escape(p.title)}</title>\n"
            f"    <link>{xml_escape(link)}</link>\n"
            f"    <guid isPermaLink=\"true\">{xml_escape(link)}</guid>\n"
            f"    <pubDate>{pub_date}</pubDate>\n"
            f"    <category>{xml_escape(p.category or 'Texnologiya')}</category>\n"
            f"    <description>{xml_escape(plain)}</description>\n"
        )
        if p.image_url:
            item += f"    <enclosure url=\"{xml_escape(p.image_url)}\" type=\"image/jpeg\"/>\n"
        item += "  </item>\n"
        items.append(item)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '<channel>\n'
        f"  <title>{xml_escape(SITE_NAME)} — Blog</title>\n"
        f"  <link>{SITE_URL}/blog</link>\n"
        f"  <description>{xml_escape(SITE_DESCRIPTION)}</description>\n"
        "  <language>uz</language>\n"
        f"  <atom:link href=\"{SITE_URL}/rss\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        + "".join(items) +
        '</channel>\n'
        '</rss>\n'
    )
    return Response(xml, mimetype='application/rss+xml')

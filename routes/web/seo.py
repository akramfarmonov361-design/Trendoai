import re
import xml.dom.minidom
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.sax.saxutils import escape as xml_escape

from flask import Response, abort, current_app, make_response, send_from_directory
from markupsafe import escape as html_escape

from models.portfolio import Portfolio
from models.post import Post
from models.service import Service
from routes.web._blueprint import web_bp
from routes.web.services_routes import SERVICES_DATA
from config import SITE_DESCRIPTION, SITE_NAME, SITE_URL
from seo_indexer import INDEXNOW_KEY

@web_bp.route('/robots.txt')
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /search",
        "Disallow: /search?",
        "Disallow: /login",
        "Disallow: /logout",
        "Allow: /static/img/",
        "Allow: /static/css/",
        "",
        "User-agent: Googlebot-Image",
        "Allow: /static/img/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")

@web_bp.route('/sitemap.xml')
def sitemap_xml():
    today = datetime.now().strftime('%Y-%m-%d')
    latest_post = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).first()
    latest_portfolio = Portfolio.query.filter_by(is_published=True).order_by(Portfolio.created_at.desc()).first()
    candidates = [today]
    if latest_post:
        cand = latest_post.updated_at or latest_post.created_at
        if cand:
            candidates.append(cand.strftime('%Y-%m-%d'))
    if latest_portfolio and latest_portfolio.created_at:
        candidates.append(latest_portfolio.created_at.strftime('%Y-%m-%d'))
    site_lastmod = max(candidates)

    pages = []
    static_pages = [
        ('/', '1.0', 'weekly', site_lastmod),
        ('/portfolio', '0.9', 'weekly', site_lastmod),
        ('/blog', '0.8', 'daily', site_lastmod),
        ('/about', '0.8', 'monthly', '2026-08-15'),
        ('/order', '0.9', 'monthly', '2026-08-15'),
        ('/maxfiylik', '0.3', 'yearly', '2026-08-15'),
        ('/terms', '0.3', 'yearly', '2026-08-15'),
    ]
    for url, priority, changefreq, lastmod in static_pages:
        pages.append({
            'loc': f'{SITE_URL}{url}',
            'priority': priority,
            'changefreq': changefreq,
            'lastmod': lastmod,
        })

    services_list = Service.query.filter_by(is_active=True).all()
    for s in services_list:
        pages.append({
            'loc': f'{SITE_URL}/services/{s.slug}',
            'priority': '0.8',
            'changefreq': 'monthly',
            'lastmod': '2026-08-15',
        })

    posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).all()
    for p in posts:
        # Exclude legacy corrupted json-* artifacts from sitemap
        clean_slug = (p.slug or '').strip().lower()
        if not clean_slug or clean_slug.startswith('json') or '```' in (p.title or ''):
            continue

        lastmod_dt = p.updated_at or p.created_at
        page_item = {
            'loc': f'{SITE_URL}/blog/{p.slug}',
            'priority': '0.7',
            'changefreq': 'monthly',
            'lastmod': lastmod_dt.strftime('%Y-%m-%d') if lastmod_dt else today,
        }
        if p.image_url:
            img_url = p.image_url if p.image_url.startswith('http') else f"{SITE_URL}{p.image_url}"
            page_item['image'] = {'loc': img_url, 'title': p.title}
        pages.append(page_item)

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for port in portfolios:
        if not port.slug:
            continue
        page_item = {
            'loc': f'{SITE_URL}/portfolio/project/{port.slug}',
            'priority': '0.6',
            'changefreq': 'monthly',
            'lastmod': port.created_at.strftime('%Y-%m-%d') if port.created_at else today,
        }
        if port.image_url:
            img_url = port.image_url if port.image_url.startswith('http') else f"{SITE_URL}{port.image_url}"
            page_item['image'] = {'loc': img_url, 'title': port.title}
        pages.append(page_item)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
    )
    for page_item in pages:
        parts.append('  <url>')
        parts.append(f'    <loc>{xml_escape(page_item["loc"])}</loc>')
        parts.append(f'    <lastmod>{page_item["lastmod"]}</lastmod>')
        parts.append(f'    <changefreq>{page_item["changefreq"]}</changefreq>')
        parts.append(f'    <priority>{page_item["priority"]}</priority>')
        img = page_item.get('image')
        if img:
            parts.append('    <image:image>')
            parts.append(f'      <image:loc>{xml_escape(img["loc"])}</image:loc>')
            parts.append(f'      <image:title>{xml_escape(img["title"] or "")}</image:title>')
            parts.append('    </image:image>')
        parts.append('  </url>')
    parts.append('</urlset>')

    return Response('\n'.join(parts), mimetype='application/xml')

@web_bp.route('/feed/facebook.xml')
def facebook_feed():
    """Facebook/Instagram Catalog Feed"""
    rss = Element('rss', {'xmlns:g': 'http://base.google.com/ns/1.0', 'version': '2.0'})
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = SITE_NAME
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'description').text = SITE_DESCRIPTION

    services_list = Service.query.filter_by(is_active=True).all()
    for s in services_list:
        item = SubElement(channel, 'item')
        SubElement(item, 'g:id').text = f"service_{s.slug}"
        SubElement(item, 'g:title').text = s.title
        SubElement(item, 'g:description').text = s.full_description or s.description
        SubElement(item, 'g:link').text = f"{SITE_URL}/services/{s.slug}"
        if s.image_url:
            img_link = s.image_url if s.image_url.startswith('http') else f"{SITE_URL}{s.image_url}"
        else:
            img_link = f"{SITE_URL}/static/images/services/{s.slug}.jpg"
        SubElement(item, 'g:image_link').text = img_link
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        raw_price = s.price or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price) or "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        item = SubElement(channel, 'item')
        SubElement(item, 'g:id').text = f"portfolio_{p.id}"
        SubElement(item, 'g:title').text = p.title
        SubElement(item, 'g:description').text = p.description
        link = f"{SITE_URL}/portfolio/project/{p.slug}" if p.slug else f"{SITE_URL}/portfolio"
        SubElement(item, 'g:link').text = link
        SubElement(item, 'g:image_link').text = p.image_url or f"{SITE_URL}/static/logo.png"
        SubElement(item, 'g:brand').text = "TrendoAI"
        SubElement(item, 'g:condition').text = "new"
        SubElement(item, 'g:availability').text = "in stock"
        raw_price = getattr(p, 'safe_price', None) or '0'
        price_numeric = re.sub(r'[^0-9]', '', raw_price) or "0"
        SubElement(item, 'g:price').text = f"{price_numeric} UZS"
        SubElement(item, 'g:custom_label_0').text = p.category
        SubElement(item, 'g:google_product_category').text = "Software > Business & Productivity Software"

    xml_str = xml.dom.minidom.parseString(tostring(rss)).toprettyxml(indent="   ")
    return Response(xml_str, mimetype='application/xml')

@web_bp.route('/api/catalog.xml')
def api_catalog_xml():
    """XML Katalog Facebook Ads va Google Merchant uchun"""
    portfolios = Portfolio.query.filter_by(is_published=True).all()
    base_url = SITE_URL

    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\\n'
    xml_data += '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\\n'
    xml_data += '<channel>\\n'
    xml_data += f'  <title>{SITE_NAME} Portfolios</title>\\n'
    xml_data += f'  <link>{base_url}/portfolio</link>\\n'
    xml_data += f'  <description>{SITE_DESCRIPTION}</description>\\n'

    cat_names = {'bot': 'Telegram Botlar', 'web': 'Veb-saytlar', 'ai': 'AI Chatbotlar', 'mobile': 'Ilovalar'}

    for item in portfolios:
        category_name = cat_names.get(item.category, item.category)
        image_url = item.image_url if item.image_url else f'{base_url}/static/favicon.svg'
        item_url = f'{base_url}/portfolio/project/{item.slug}' if item.slug else f'{base_url}/portfolio'

        xml_data += '  <item>\\n'
        xml_data += f'    <g:id>{item.id}</g:id>\\n'
        xml_data += f'    <title>{xml_escape(item.title)}</title>\\n'
        xml_data += f'    <link>{item_url}</link>\\n'
        xml_data += f'    <description><![CDATA[{item.description}]]></description>\\n'
        xml_data += f'    <g:image_link>{image_url}</g:image_link>\\n'
        xml_data += '    <g:brand>TrendoAI</g:brand>\\n'
        xml_data += '    <g:condition>new</g:condition>\\n'
        xml_data += '    <g:availability>in stock</g:availability>\\n'
        xml_data += '    <g:price>0 UZS</g:price>\\n'
        xml_data += f'    <g:product_type>{category_name}</g:product_type>\\n'
        xml_data += '    <g:google_product_category>Software &gt; Computer Software &gt; Business &amp; Productivity Software</g:google_product_category>\\n'

        if item.meta_keywords:
            for keyword in item.meta_keywords.split(',')[:5]:
                xml_data += f'    <g:custom_label_0>{xml_escape(keyword.strip())}</g:custom_label_0>\\n'
        xml_data += '  </item>\\n'

    xml_data += '</channel>\\n'
    xml_data += '</rss>'
    return Response(xml_data, mimetype='application/xml')

def _resolve_feed_image(image_url, title, category, item_id, site_url):
    """Har bir xizmat yoki keys uchun saytdagi aniq rasmni, bo'lmasa mavzuli sifatli rasmni olish"""
    if image_url and str(image_url).strip():
        img = str(image_url).strip()
        if not any(img.endswith(x) for x in ('og-image.jpg', 'hero-social.png', '.svg')):
            if not img.startswith('http'):
                # WebP o'rniga Meta uchun JPG
                img = img.replace('.webp', '.jpg')
                return f"{site_url}{img if img.startswith('/') else '/' + img}?v=2026_sep"
            return img

    t_lower = (title or '').lower()
    cat_lower = (category or '').lower()

    if any(w in t_lower for w in ['insta', 'dub', 'video', 'dublyaj']):
        return f"{site_url}/static/img/portfolio/instadubuz.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['bolajon', 'english', 'bola']):
        return f"{site_url}/static/img/portfolio/bolajon-ai-english.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['botfactory', 'chatbot factory', 'factory']):
        return f"{site_url}/static/img/portfolio/botfactory.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['ism', 'ismlar']):
        return f"{site_url}/static/img/portfolio/ismlar-manosi-ai.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['luxe', 'kiyim', 'brend']):
        return f"{site_url}/static/img/portfolio/luxe-core.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['optom', 'optombazar']):
        return f"{site_url}/static/img/portfolio/optombazar.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['restoran', 'voice ai delivery', 'ovqat', 'fastfood']):
        return f"{site_url}/static/img/portfolio/restoran.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['mijoz', 'finder', 'lid', 'topar']):
        return f"{site_url}/static/img/portfolio/mijoz-topar.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['text', 'ovoz', 'speech', 'diktor']):
        return f"{site_url}/static/img/portfolio/text-ovoz.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['nova', 'novatech']):
        return f"{site_url}/static/img/portfolio/novatech.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['real', 'smart', 'rieltor']):
        return f"{site_url}/static/img/portfolio/real-smart-ai.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['paket', 'qadoq', 'assistent']):
        return f"{site_url}/static/img/portfolio/paketshop-assistent.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['texno', 'elektronika']):
        return f"{site_url}/static/img/portfolio/texnomarket.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['speak', 'trendospeak']):
        return f"{site_url}/static/img/portfolio/trendospeak.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['uzum', 'yetkazib']):
        return f"{site_url}/static/img/portfolio/uzum-tezkor.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['vibe', 'kodlash', 'kurs']):
        return f"{site_url}/static/img/portfolio/vibecoding.jpg?v=2026_sep"
    elif any(w in t_lower for w in ['viral', 'reels', 'tiktok']):
        return f"{site_url}/static/img/portfolio/viral-video.jpg?v=2026_sep"
    elif cat_lower == 'bot' or 'bot' in t_lower:
        return f"{site_url}/static/img/portfolio/botfactory.jpg?v=2026_sep"
    elif cat_lower == 'ai' or 'ai' in t_lower:
        return f"{site_url}/static/img/portfolio/instadubuz.jpg?v=2026_sep"
    return f"{site_url}/static/img/portfolio/trendoai-uz.jpg?v=2026_sep"

def _resolve_feed_video(p, site_url):
    """Loyiha uchun to'g'ridan-to'g'ri MP4 video havolasini aniqlash"""
    if not p:
        return ""
    v_url = (getattr(p, 'video_url', None) or '').strip()
    if v_url.endswith('.mp4'):
        if v_url.startswith('http'):
            return v_url
        return f"{site_url}{v_url}"

    t_lower = (getattr(p, 'title', None) or '').lower()
    s_lower = (getattr(p, 'slug', None) or '').lower()
    combined = f"{t_lower} {s_lower}"
    if 'botfactory' in combined:
        return f"{site_url}/static/videos/botfactory-demo.mp4"
    elif 'luxe' in combined:
        return f"{site_url}/static/videos/luxe-core-demo.mp4"
    elif 'quiz' in combined:
        return f"{site_url}/static/videos/quiz-video-generator-demo.mp4"
    elif 'real-smart' in combined or 'realsmart' in combined:
        return f"{site_url}/static/videos/realsmart-ai-demo.mp4"
    elif 'insta' in combined or 'dub' in combined:
        return f"{site_url}/static/videos/instadub-demo.mp4"
    return ""

def _format_feed_price(raw_price, default_amount=700000):
    """Narxni Meta Commerce kutgan 'XXXXXX UZS' ko'rinishiga keltiradi."""
    if raw_price:
        cleaned = re.sub(r'[^\d]', '', str(raw_price))
        if cleaned:
            return f"{cleaned} UZS"
    return f"{default_amount} UZS"

@web_bp.route('/facebook-catalog.xml')
@web_bp.route('/facebook-feed.xml')
@web_bp.route('/api/catalog/facebook.xml')
@web_bp.route('/feed/facebook-catalog.xml')
@web_bp.route('/meta-catalog.xml')
def facebook_catalog_feed():
    """Facebook & Meta Commerce Manager uchun Dynamic Product Catalog Feed"""
    from services.cache_service import cache_get, cache_set
    is_testing = bool(current_app.config.get('TESTING'))
    cache_key = "meta_catalog_feed_xml"
    cached_xml = cache_get(cache_key, is_testing=is_testing)
    if cached_xml:
        return Response(cached_xml, mimetype='application/xml')

    site_url = SITE_URL.rstrip('/')
    site_name = SITE_NAME

    items_xml = []
    services_list = Service.query.filter_by(is_active=True).all()
    if not services_list:
        # Fallback to core SERVICES_DATA
        for key, s in SERVICES_DATA.items():
            item_id = f"service_{key}"
            title = s.get('title', 'IT Xizmat')
            desc = s.get('full_description') or s.get('description') or f"TrendoAI {title} xizmati"
            link = f"{site_url}/services/{key}"
            img = _resolve_feed_image(None, title, key, item_id, site_url)
            price_str = "500000 UZS"
            if key == 'telegram_bot':
                price_str = "400000 UZS"
            elif key == 'web_site':
                price_str = "700000 UZS"
            elif key == 'ai_chatbot':
                price_str = "1200000 UZS"
            elif key == 'target_ads':
                price_str = "600000 UZS"

            items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>IT Services</g:product_type>
      <g:custom_label_0>Service</g:custom_label_0>
    </item>""")
    else:
        for s in services_list:
            item_id = f"service_{s.id}"
            title = s.title or "IT Xizmat"
            desc = s.description or s.meta_desc or f"TrendoAI {title} xizmati"
            link = f"{site_url}/services/{s.slug}" if s.slug else f"{site_url}/services"
            img = _resolve_feed_image(s.image_url, title, getattr(s, 'category', 'service'), item_id, site_url)

            price_str = _format_feed_price(s.price, default_amount=700000)

            items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>IT Services</g:product_type>
      <g:custom_label_0>Service</g:custom_label_0>
    </item>""")

    portfolios = Portfolio.query.filter_by(is_published=True).all()
    for p in portfolios:
        item_id = f"portfolio_{p.id}"
        title = p.title or "Portfolio Loyiha"
        desc = p.description or f"TrendoAI tomonidan yaratilgan {title} loyihasi"
        link = f"{site_url}/portfolio/project/{p.slug}" if p.slug else f"{site_url}/portfolio"
        img = _resolve_feed_image(p.image_url, title, p.category, item_id, site_url)
        price_str = _format_feed_price(p.price, default_amount=1500000)
        v_link = _resolve_feed_video(p, site_url)
        v_tag = f"\n      <g:video_link>{xml_escape(v_link)}</g:video_link>" if v_link else ""

        items_xml.append(f"""    <item>
      <g:id>{xml_escape(item_id)}</g:id>
      <g:title>{xml_escape(title)}</g:title>
      <g:description>{xml_escape(desc)}</g:description>
      <g:link>{xml_escape(link)}</g:link>
      <g:image_link>{xml_escape(img)}</g:image_link>{v_tag}
      <g:brand>{xml_escape(site_name)}</g:brand>
      <g:condition>new</g:condition>
      <g:availability>in stock</g:availability>
      <g:price>{xml_escape(price_str)}</g:price>
      <g:product_type>Portfolio Case Study</g:product_type>
      <g:custom_label_0>Portfolio</g:custom_label_0>
    </item>""")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>{xml_escape(site_name)} Products Catalog</title>
    <link>{xml_escape(site_url)}</link>
    <description>Official Dynamic Product Catalog Feed for Meta Ads</description>
{chr(10).join(items_xml)}
  </channel>
</rss>"""
    cache_set(cache_key, xml_content, ttl=3600, is_testing=is_testing)
    return Response(xml_content, mimetype='application/xml')

@web_bp.route('/indexnow-key.txt')
@web_bp.route(f'/{INDEXNOW_KEY}.txt')
@web_bp.route('/trendoai_indexnow_key_2026.txt')  # eskirgan manzil, orqaga moslik
def indexnow_key_file():
    return Response(INDEXNOW_KEY, mimetype='text/plain')

VERIFICATION_CODE_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,64}')

@web_bp.route('/google<verification_code>.html')
def google_verification(verification_code):
    if not VERIFICATION_CODE_PATTERN.fullmatch(verification_code):
        abort(404)
    return Response(
        f'google-site-verification: google{verification_code}.html',
        mimetype='text/plain',
    )

@web_bp.route('/yandex_<verification_code>.html')
def yandex_verification(verification_code):
    if not VERIFICATION_CODE_PATTERN.fullmatch(verification_code):
        abort(404)
    html_content = f'''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: {html_escape(verification_code)}</body>
</html>'''
    return Response(html_content, mimetype='text/html')

@web_bp.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response

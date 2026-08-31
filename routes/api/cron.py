import random
import threading
from datetime import datetime
from flask import jsonify, request
from config import CATEGORIES, GEMINI_API_KEY, GEMINI_MODEL, SITE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
from extensions import db
from models.post import Post
from routes.api._blueprint import api_bp, _has_valid_cron_secret, _cron_secret_error

# ========== CRON ROUTES ==========

@api_bp.route('/api/cron/status')
def cron_status():
    """Cron vazifalar statusi"""
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        return jsonify({
            'status': 'ok',
            'scheduled_jobs': len(jobs),
            'jobs': jobs,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/cron/generate', methods=['GET', 'POST'])
def cron_generate_post():
    """Tashqi cron xizmatlari uchun post generatsiyasini web fonida boshlash."""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    topic = request.args.get('topic')
    category = request.args.get('category')

    from scheduler import generate_and_publish_post
    thread = threading.Thread(target=generate_and_publish_post, args=(topic, category), daemon=True)
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Post generation web fonida boshlandi',
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/api/cron/keep-alive')
def cron_keep_alive():
    """Serverni uyg'oq saqlash"""
    status_data = {
        'status': 'alive',
        'time': datetime.now().isoformat()
    }
    try:
        from scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()
        status_data['scheduler_status'] = 'running' if len(jobs) > 0 else 'stopped'
        status_data['active_jobs_count'] = len(jobs)
    except Exception as e:
        status_data['scheduler_error'] = str(e)

    return jsonify(status_data)


@api_bp.route('/api/cron/debug-generate')
def cron_debug_generate():
    """Sinxron debug endpoint"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    import traceback as tb
    result = {'steps': [], 'success': False}

    try:
        result['gemini_api_key_exists'] = bool(GEMINI_API_KEY)
        result['gemini_model'] = GEMINI_MODEL
        if not GEMINI_API_KEY:
            result['error'] = "GEMINI_API_KEY muhit o'zgaruvchisi topilmadi!"
            return jsonify(result), 500

        result['steps'].append('1. Gemini API oddiy test...')
        try:
            from google import genai
            test_client = genai.Client(api_key=GEMINI_API_KEY)
            test_response = test_client.models.generate_content(model=GEMINI_MODEL, contents="Salom, 1+1 nechta?")
            resp_text = (getattr(test_response, "text", "") or "")[:100]
            result['steps'].append(f'✅ Gemini API ishlaydi! Javob: {resp_text}')
            result['gemini_test'] = 'OK'
        except Exception as gemini_err:
            result['steps'].append(f'❌ Gemini API xatosi: {str(gemini_err)}')
            result['gemini_error'] = str(gemini_err)
            return jsonify(result), 500

        result['steps'].append('2. AI post generatsiya boshlanmoqda...')
        from services.ai_service import generate_post_for_seo
        from scheduler import TOPICS
        topic = request.args.get('topic') or random.choice(TOPICS)
        result['topic'] = topic

        post_data = generate_post_for_seo(topic)
        if not post_data:
            result['error'] = 'generate_post_for_seo None qaytardi'
            return jsonify(result), 500

        result['steps'].append(f'✅ AI generatsiya muvaffaqiyatli: {post_data.get("title", "?")}')

        from image_fetcher import get_image_for_topic, build_image_prompt
        existing_urls = [
            row[0] for row in db.session.query(Post.image_url)
            .filter(Post.image_url.isnot(None), Post.image_url.contains('images.unsplash.com')).all()
        ]
        image_url = get_image_for_topic(topic, exclude_image_urls=existing_urls)
        image_prompt = build_image_prompt(topic=topic, title=post_data.get('title'), category=request.args.get('category'))

        selected_category = request.args.get('category') or random.choice(CATEGORIES)
        new_post = Post(
            title=post_data['title'],
            content=post_data['content'],
            topic=topic,
            category=selected_category,
            keywords=post_data.get('keywords', ''),
            image_url=image_url,
            image_prompt=image_prompt,
            is_published=True
        )
        new_post.reading_time = new_post.calculate_reading_time()
        db.session.add(new_post)
        db.session.commit()

        new_post.slug = new_post.generate_slug()
        db.session.commit()

        result['steps'].append(f'✅ Bazaga saqlandi: ID={new_post.id}, slug={new_post.slug}')
        result['post_id'] = new_post.id
        result['post_url'] = f'{SITE_URL}/blog/{new_post.slug}'
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = tb.format_exc()
        return jsonify(result), 500


@api_bp.route('/api/cron/test-ai')
def cron_test_ai():
    """Tezkor Gemini API test"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    result = {
        'api_key_exists': bool(GEMINI_API_KEY),
        'model': GEMINI_MODEL,
    }
    if not GEMINI_API_KEY:
        result['error'] = 'GEMINI_API_KEY topilmadi'
        return jsonify(result), 500

    try:
        from google import genai
        test_client = genai.Client(api_key=GEMINI_API_KEY)
        resp = test_client.models.generate_content(model=GEMINI_MODEL, contents="1+1=?")
        result['gemini_status'] = 'OK'
        result['gemini_response'] = (getattr(resp, "text", "") or "")[:200]
    except Exception as e:
        result['gemini_status'] = 'ERROR'
        result['gemini_error'] = str(e)

    try:
        result['db_status'] = 'OK'
        result['total_posts'] = Post.query.count()
    except Exception as e:
        result['db_status'] = 'ERROR'
        result['db_error'] = str(e)

    result['telegram_token_exists'] = bool(TELEGRAM_BOT_TOKEN)
    result['telegram_channel_exists'] = bool(TELEGRAM_CHANNEL_ID)
    return jsonify(result)

import os
from datetime import datetime
from flask import jsonify, request, current_app
from sqlalchemy import text
from extensions import csrf, db
from models.order import BotOrder, Order
from models.interaction import Lead, PushSubscription
from models.post import Post
from routes.admin import login_required
from config import CATEGORIES
from services.crm_service import is_duplicate_contact
from services.push_service import notify_all_subscribers
from routes.api._blueprint import api_bp, _client_ip, _check_rate_limit, _verify_meta_signature, _has_valid_cron_secret, _cron_secret_error
from utils.logger import setup_logger
logger = setup_logger("public")



# ========== PUBLIC API ROUTES ==========

@api_bp.route('/api/health')
def api_health():
    """Health check endpoint.

    Render shu manzil orqali servis sog'ligini tekshiradi. Ilgari bu yerda
    faqat statik JSON qaytarilardi, shuning uchun baza butunlay yiqilgan
    bo'lsa ham "ok" javob kelib, avtomatik restart ishga tushmasdi.
    Endi bazaga eng yengil so'rov yuboriladi va nosozlikda 503 qaytadi.
    """
    payload = {
        'status': 'ok',
        'service': 'TrendoAI',
        'version': '2.0.0',
        'database': 'ok',
        'timestamp': datetime.now().isoformat()
    }
    try:
        db.session.execute(text('SELECT 1'))
    except Exception as exc:
        db.session.rollback()
        logger.error(f"[health] Baza tekshiruvi muvaffaqiyatsiz: {exc}")
        payload['status'] = 'error'
        payload['database'] = 'error'
        return jsonify(payload), 503

    return jsonify(payload)


@api_bp.route('/api/posts')
def api_posts():
    """Barcha postlar API"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', None)

    query = Post.query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=min(per_page, 50), error_out=False
    )

    return jsonify({
        'posts': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })


@api_bp.route('/api/posts/<int:post_id>')
def api_post(post_id):
    """Bitta post API"""
    p = Post.query.get_or_404(post_id)
    return jsonify(p.to_dict())


@api_bp.route('/api/stats')
def api_stats():
    """Statistika API"""
    return jsonify({
        'total_posts': Post.query.count(),
        'published_posts': Post.query.filter_by(is_published=True).count(),
        'total_views': db.session.query(db.func.sum(Post.views)).scalar() or 0,
        'categories': CATEGORIES
    })


@api_bp.route('/api/lead', methods=['POST'])
@csrf.exempt
def submit_lead():
    """Lead Magnet yoki Chatbot orqali kelgan ma'lumotni saqlash"""
    client_ip = _client_ip()
    if not _check_rate_limit(f"lead:{client_ip}", limit=5, window_seconds=600):
        return jsonify({
            'status': 'error',
            'message': "Juda ko'p ariza yuborildi. Iltimos, birozdan so'ng qayta urinib ko'ring."
        }), 429

    data = request.get_json(silent=True) or {}
    contact = (data.get('contact') or '').strip()
    if not contact:
        return jsonify({'status': 'error', 'message': "Iltimos, aloqa ma'lumotini kiriting."}), 400

    name = (data.get('name') or "Noma'lum").strip()
    source = (data.get('source') or 'Sayt Orqali').strip()
    if len(contact) > 100 or len(name) > 100 or len(source) > 50:
        return jsonify({'status': 'error', 'message': "Yuborilgan ma'lumot juda uzun."}), 400

    # Takroriy kontakt bazani ham, adminning Telegramini ham spam qilmasligi uchun
    # yangi yozuv ochilmaydi, lekin mijozga xato ko'rsatilmaydi.
    if is_duplicate_contact(contact):
        return jsonify({'status': 'success', 'message': "Ma'lumot allaqachon qabul qilingan!"})

    try:
        new_lead = Lead(name=name, contact=contact, source=source)
        db.session.add(new_lead)
        db.session.commit()

        from telegram_poster import send_admin_alert
        msg = f"🎯 <b>YANGI MIJOZ (LEAD)!</b>\n\n👤 <b>Ismi:</b> {new_lead.name}\n📞 <b>Aloqa:</b> {new_lead.contact}\n📍 <b>Manba:</b> {new_lead.source}"
        send_admin_alert(msg)

        return jsonify({'status': 'success', 'message': "Ma'lumot muvaffaqiyatli qabul qilindi!"})
    except Exception as e:
        db.session.rollback()
        # Ichki xato matni mijozga chiqarilmaydi — faqat logga yoziladi.
        logger.error(f"[api] Lead error: {e}")
        return jsonify({'status': 'error', 'message': "Ma'lumotni saqlashda xato yuz berdi."}), 500


# ========== PUSH NOTIFICATION ROUTES ==========

@api_bp.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    """Web Push obunasini saqlash yoki yangilash"""
    if not _check_rate_limit(f"push:{_client_ip()}", limit=10, window_seconds=600):
        return jsonify({'error': "Juda ko'p so'rov yuborildi."}), 429

    data = request.get_json(silent=True) or {}
    if not data or not data.get('endpoint'):
        return jsonify({'error': 'Invalid data'}), 400

    endpoint = data['endpoint']
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not p256dh or not auth:
        return jsonify({'error': 'Missing keys'}), 400

    subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
    created = False

    if not subscription:
        subscription = PushSubscription(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth
        )
        db.session.add(subscription)
        created = True
    else:
        subscription.p256dh = p256dh
        subscription.auth = auth

    db.session.commit()
    logger.info(f"[push] Subscription {'yaratildi' if created else 'yangilandi'}: {endpoint[:80]}")
    return jsonify({'success': True, 'message': 'Obuna saqlandi', 'created': created})


@api_bp.route('/api/push/send', methods=['POST'])
@login_required
def push_send():
    """Push xabar yuborish (Admin)"""
    data = request.json or {}
    title = data.get('title', 'TrendoAI')
    message = data.get('message', 'Yangi xabar!')
    url = data.get('url', '/')

    sent_count = notify_all_subscribers(title=title, message=message, url=url)
    return jsonify({'success': sent_count > 0, 'sent_count': sent_count})


# ========== ADMIN / BOT STATUS APIS ==========

@api_bp.route('/api/bot-order-status', methods=['POST'])
@login_required
def update_bot_order_status():
    """Bot buyurtma statusini o'zgartirish"""
    try:
        order_id = (request.json or {}).get('order_id') or request.form.get('order_id')
        status = (request.json or {}).get('status') or request.form.get('status')
        order = db.session.get(BotOrder, order_id)
        if order:
            order.status = status
            db.session.commit()

            from telegram_poster import bot
            if bot and order.tg_id:
                status_text = {
                    'confirmed': "✅ Qabul qilindi",
                    'preparing': "👨‍🍳 Tayyorlanmoqda",
                    'delivering': "🛵 Yetkazilmoqda",
                    'done': "🎉 Yetkazib berildi",
                    'cancelled': "❌ Bekor qilindi"
                }.get(status, status)

                msg = f"📋 Buyurtma {order.order_number} yangilandi!\n📦 Status: *{status_text}*"
                try:
                    bot.send_message(order.tg_id, msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to send status update to customer: {e}")

            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/admin/crm/update-status', methods=['POST'])
@login_required
@csrf.exempt
def api_crm_update_status():
    """AJAX status update for Kanban Board items"""
    data = request.json or {}
    item_type = data.get('type')
    item_id = data.get('id')
    new_status = data.get('status')

    valid_statuses = ['new', 'contacted', 'in_progress', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Yaroqsiz status'}), 400

    try:
        if item_type == 'order':
            order = db.session.get(Order, item_id)
            if order:
                order.status = new_status
                db.session.commit()
                return jsonify({'success': True, 'message': f'Order #{item_id} statusi yangilandi.'})
        elif item_type == 'lead':
            lead = db.session.get(Lead, item_id)
            if lead:
                lead.status = new_status
                db.session.commit()
                return jsonify({'success': True, 'message': f'Lead #{item_id} statusi yangilandi.'})

        return jsonify({'error': 'Topilmadi'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/admin/crm/update-note', methods=['POST'])
@login_required
@csrf.exempt
def api_crm_update_note():
    """AJAX endpoint for saving follow-up notes on Kanban items"""
    data = request.json or {}
    item_type = data.get('type')
    item_id = data.get('id')
    note = (data.get('note') or '').strip()

    try:
        if item_type == 'order':
            order = db.session.get(Order, item_id)
            if order:
                order.admin_note = note
                db.session.commit()
                return jsonify({'success': True, 'message': 'Eslatma saqlandi.'})
        elif item_type == 'lead':
            lead = db.session.get(Lead, item_id)
            if lead:
                lead.admin_note = note
                db.session.commit()
                return jsonify({'success': True, 'message': 'Eslatma saqlandi.'})

        return jsonify({'error': 'Element topilmadi'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/api/generate-portfolio')
@login_required
def api_generate_portfolio():
    """AI yordamida portfolio kontent generatsiya qilish"""
    from services.ai_service import generate_portfolio_content
    title = request.args.get('title', '')
    category = request.args.get('category', 'web')

    if not title:
        return jsonify({'error': 'Title kerak'}), 400

    try:
        result = generate_portfolio_content(title, category)
        if result:
            return jsonify(result)
        return jsonify({'error': 'AI generatsiya muvaffaqiyatsiz'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/init-db')
def api_init_database():
    """Database jadvallarini tekshirish"""
    if not _has_valid_cron_secret():
        return _cron_secret_error()

    try:
        db.create_all()
        order_count = Order.query.count()
        post_count = Post.query.count()
        return jsonify({
            'status': 'success',
            'message': 'Database jadvallar muvaffaqiyatli yaratildi/yangilandi',
            'tables': {
                'orders': order_count,
                'posts': post_count
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@api_bp.route('/api/webhook/facebook-leads', methods=['GET', 'POST'])
def facebook_lead_webhook():
    """
    Meta Instant Lead Forms Webhook.
    Instagram / Facebook ichida to'ldirilgan arizalarni qabul qilib,
    avtomatik bazaga (Order) saqlaydi va Telegramga tezkor xabar beradi.
    """
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        expected_token = os.getenv('FB_LEAD_VERIFY_TOKEN', 'trendoai_lead_secret_2026')
        if mode == 'subscribe' and token == expected_token:
            return challenge or 'OK', 200
        return jsonify({'error': 'Invalid verification token'}), 403

    if not _verify_meta_signature():
        return jsonify({'error': 'Invalid signature'}), 403

    data = request.get_json(silent=True) or {}
    try:
        from config import FB_CONVERSIONS_API_TOKEN
        import requests
        from telegram_poster import send_admin_alert

        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                if change.get('field') == 'leadgen':
                    leadgen_id = change.get('value', {}).get('leadgen_id')
                    form_id = change.get('value', {}).get('form_id')

                    # leadgen_id tashqaridan keladi: raqam bo'lmasa Graph API
                    # manzilining yo'l qismini o'zgartirib yuborishi mumkin.
                    if leadgen_id and not str(leadgen_id).isdigit():
                        current_app.logger.warning(
                            "Facebook Lead Webhook: yaroqsiz leadgen_id e'tiborsiz qoldirildi"
                        )
                        continue

                    if leadgen_id and FB_CONVERSIONS_API_TOKEN:
                        url = f"https://graph.facebook.com/v19.0/{leadgen_id}"
                        resp = requests.get(
                            url,
                            headers={'Authorization': f'Bearer {FB_CONVERSIONS_API_TOKEN}'},
                            timeout=5,
                        )
                        if resp.status_code == 200:
                            lead_data = resp.json()
                            field_data = {f.get('name'): f.get('values', [''])[0] for f in lead_data.get('field_data', [])}

                            full_name = field_data.get('full_name') or field_data.get('name') or 'Instagram Mijoz'
                            phone = field_data.get('phone_number') or field_data.get('phone') or 'Kiritilmagan'
                            service_choice = field_data.get('service') or field_data.get('xizmat') or 'Meta Instant Form'

                            order = Order(
                                name=full_name,
                                phone=phone,
                                service='meta_lead_form',
                                service_name=service_choice,
                                message=f"Instagram Instant Form #{form_id} orqali keldi",
                                status='new'
                            )
                            db.session.add(order)
                            db.session.commit()

                            time_str = datetime.now().strftime('%d.%m.%Y %H:%M')
                            alert_msg = f"""🔥 <b>YANGI INSTAGRAM INSTANT FORM ARIZASI!</b>

👤 <b>Mijoz:</b> {full_name}
📞 <b>Telefon:</b> {phone}
🛠 <b>Xizmat:</b> {service_choice}
📱 <b>Manba:</b> Instagram Lead Form #{form_id}
⏰ <b>Vaqt:</b> {time_str}
"""
                            send_admin_alert(alert_msg)
    except Exception as exc:
        current_app.logger.warning("Facebook Lead Webhook error: %s", exc)

    return jsonify({'status': 'received'}), 200

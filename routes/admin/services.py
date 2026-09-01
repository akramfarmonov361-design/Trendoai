import re
from flask import flash, jsonify, redirect, render_template, request, url_for
from extensions import db
from models.service import Service
from routes.admin._blueprint import admin_bp, login_required
from utils.logger import setup_logger
logger = setup_logger("services")


# ========== SERVICE ADMIN ROUTES ==========

@admin_bp.route('/admin/services/generate', methods=['POST'])
@login_required
def admin_service_generate():
    """AI yordamida xizmat ma'lumotlarini generatsiya qilish"""
    try:
        from services.ai_service import generate_custom_content
        import json

        title = (request.json or {}).get('title', '')
        if not title:
            return jsonify({'error': 'Sarlavha (title) kiritilmagan'}), 400

        prompt = f"""
Sen professional IT xizmatlar uchun kontent yozuvchisan. O'zbek tilida yoz.
Quyidagi xizmat uchun kontent yarat:

Xizmat nomi: {title}

Quyidagi formatda JSON qaytaring (faqat JSON, boshqa matn yo'q):
{{
    "description": "1-2 gaplik jozibali qisqa tavsif (tagline)",
    "full_description": "3-4 gaplik to'liq professional tavsif. Mijozga qanday foyda keltirishini yoz.",
    "features": ["Xususiyat 1", "Xususiyat 2", "Xususiyat 3", "Xususiyat 4"],
    "meta_desc": "SEO uchun 150 belgidan kam meta description",
    "icon": "Mos emoji (bitta)",
    "slug": "english-slug-format"
}}
"""
        text = (generate_custom_content(prompt) or "").strip()
        if not text:
            return jsonify({'error': 'AI generatsiya muvaffaqiyatsiz'}), 500

        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]

        data = json.loads(text)
        return jsonify(data)
    except Exception as e:
        logger.error(f"[admin] AI Service Generation Error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/services')
@login_required
def admin_services():
    """Xizmatlar ro'yxati"""
    services_list = Service.query.order_by(Service.order.asc()).all()
    return render_template('admin/services.html', services=services_list)


@admin_bp.route('/admin/services/new', methods=['GET', 'POST'])
@login_required
def admin_service_new():
    """Yangi xizmat qo'shish"""
    if request.method == 'POST':
        try:
            slug = request.form.get('slug')
            if not slug:
                slug = re.sub(r'[^a-z0-9-]', '', (request.form.get('title') or '').lower().replace(' ', '-'))

            service = Service(
                slug=slug,
                title=request.form.get('title'),
                description=request.form.get('description'),
                full_description=request.form.get('full_description'),
                price=request.form.get('price'),
                icon=request.form.get('icon', '🚀'),
                image_url=request.form.get('image_url'),
                features=request.form.get('features'),
                is_active=request.form.get('is_active') == 'on',
                order=int(request.form.get('order', 0)),
                meta_desc=request.form.get('meta_desc'),
                discount_percent=int(request.form.get('discount_percent', 0)),
                discount_until=request.form.get('discount_until')
            )
            db.session.add(service)
            db.session.commit()

            # Xizmatlar katalog feediga kiradi
            try:
                from services.cache_service import clear_catalog_cache
                clear_catalog_cache()
            except Exception:
                pass
            flash(f'"{service.title}" muvaffaqiyatli qo\'shildi!', 'success')
            return redirect(url_for('admin.admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')

    return render_template('admin/service_form.html', service=None)


@admin_bp.route('/admin/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_service_edit(service_id):
    """Xizmatni tahrirlash"""
    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        try:
            service.slug = request.form.get('slug')
            service.title = request.form.get('title')
            service.description = request.form.get('description')
            service.full_description = request.form.get('full_description')
            service.price = request.form.get('price')
            service.icon = request.form.get('icon')
            service.image_url = request.form.get('image_url')
            service.features = request.form.get('features')
            service.is_active = request.form.get('is_active') == 'on'
            service.order = int(request.form.get('order', 0))
            service.meta_desc = request.form.get('meta_desc')
            service.discount_percent = int(request.form.get('discount_percent', 0))
            service.discount_until = request.form.get('discount_until')

            db.session.commit()

            # Xizmatlar katalog feediga kiradi
            try:
                from services.cache_service import clear_catalog_cache
                clear_catalog_cache()
            except Exception:
                pass
            flash(f'"{service.title}" yangilandi!', 'success')
            return redirect(url_for('admin.admin_services'))
        except Exception as e:
            flash(f'Xatolik: {e}', 'error')

    return render_template('admin/service_form.html', service=service)


@admin_bp.route('/admin/services/<int:service_id>/delete', methods=['POST'])
@login_required
def admin_service_delete(service_id):
    """Xizmatni o'chirish"""
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()

    # Xizmatlar katalog feediga kiradi
    try:
        from services.cache_service import clear_catalog_cache
        clear_catalog_cache()
    except Exception:
        pass
    flash('Xizmat o\'chirildi!', 'success')
    return redirect(url_for('admin.admin_services'))

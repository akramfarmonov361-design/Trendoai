from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from extensions import db
from models.order import BotOrder, Order
from models.interaction import Lead
from routes.admin._blueprint import admin_bp, login_required

# ========== ORDER & KANBAN ROUTES ==========

@admin_bp.route('/admin/bot-orders')
@login_required
def admin_bot_orders():
    """Bot orqali tushgan menyu buyurtmalarini boshqarish"""
    orders = BotOrder.query.order_by(BotOrder.created_at.desc()).all()
    return render_template('admin/bot_orders.html', orders=orders)


@admin_bp.route('/admin/orders')
@login_required
def admin_orders():
    """Barcha buyurtmalarni ko'rish"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)

    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    new_count = Order.query.filter_by(status='new').count()
    total_count = Order.query.count()

    return render_template('admin/orders.html',
                           orders=orders,
                           new_count=new_count,
                           total_count=total_count,
                           current_status=status_filter)


@admin_bp.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    """Buyurtma statusini yangilash"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if new_status in ['new', 'contacted', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Buyurtma #{order.id} statusi yangilandi!', 'success')

    return redirect(url_for('admin.admin_orders'))


@admin_bp.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def admin_delete_order(order_id):
    """Buyurtmani o'chirish"""
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash(f'Buyurtma #{order_id} o\'chirildi!', 'success')
    return redirect(url_for('admin.admin_orders'))


@admin_bp.route('/admin/kanban')
@login_required
def admin_kanban():
    """CRM Kanban Board va Sotuvlar Analitikasi"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    leads = Lead.query.order_by(Lead.created_at.desc()).all()

    kanban_data = {
        'new': [],
        'contacted': [],
        'in_progress': [],
        'completed': [],
        'cancelled': []
    }

    for o in orders:
        st = o.status if o.status in kanban_data else 'new'
        kanban_data[st].append({
            'type': 'order',
            'id': o.id,
            'name': o.name,
            'contact': o.phone,
            'title': o.service_name,
            'budget': o.budget or 'Kelishilgan',
            'message': o.message,
            'admin_note': o.admin_note or '',
            'status': st,
            'date': o.created_at.strftime('%d.%m.%Y %H:%M') if o.created_at else 'N/A'
        })

    for l in leads:
        st = l.status if l.status in kanban_data else 'new'
        kanban_data[st].append({
            'type': 'lead',
            'id': l.id,
            'name': l.name or 'Lead Mijoz',
            'contact': l.contact,
            'title': f"Lead ({l.source})",
            'budget': 'Ma\'lumot berilmagan',
            'message': f"Manba: {l.source}",
            'admin_note': l.admin_note or '',
            'status': st,
            'date': l.created_at.strftime('%d.%m.%Y %H:%M') if l.created_at else 'N/A'
        })

    total_items = len(orders) + len(leads)
    completed_count = len(kanban_data['completed'])
    conversion_rate = round((completed_count / total_items * 100), 1) if total_items > 0 else 0

    stats = {
        'total': total_items,
        'new': len(kanban_data['new']),
        'contacted': len(kanban_data['contacted']),
        'in_progress': len(kanban_data['in_progress']),
        'completed': completed_count,
        'cancelled': len(kanban_data['cancelled']),
        'conversion_rate': conversion_rate
    }

    return render_template('admin/kanban.html', kanban=kanban_data, stats=stats)


@admin_bp.route('/admin/invoice/<int:order_id>')
@login_required
def admin_invoice(order_id):
    """Buyurtma bo'yicha professional hisob-faktura (Invoice & Contract) sahifasi"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/invoice.html', order=order, now=datetime.now())

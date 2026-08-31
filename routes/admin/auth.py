import time
from flask import flash, redirect, render_template, request, session, url_for
from extensions import db
from models.post import Post
from models.order import Order
from models.portfolio import Portfolio
from routes.admin._blueprint import (
    admin_bp,
    login_required,
    _client_ip,
    _prune_failed_logins,
    _failed_logins,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    _check_admin_credentials
)

# ========== AUTH ROUTES ==========

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login sahifasi"""
    if session.get('logged_in'):
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        ip = _client_ip()
        now = time.time()
        _prune_failed_logins(now)
        attempts = [t for t in _failed_logins.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]

        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            _failed_logins[ip] = attempts
            flash("Juda ko'p urinish. 15 daqiqadan so'ng qayta urinib ko'ring.", 'error')
            return render_template('admin/login.html'), 429

        username = request.form.get('username')
        password = request.form.get('password')

        if _check_admin_credentials(username, password):
            _failed_logins.pop(ip, None)
            session['logged_in'] = True
            session['username'] = username
            session['last_active'] = time.time()
            flash('Tizimga muvaffaqiyatli kirdingiz!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            attempts.append(now)
            _failed_logins[ip] = attempts
            flash('Login yoki parol noto\'g\'ri!', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/admin/logout')
def admin_logout():
    """Chiqish"""
    session.clear()
    flash('Tizimdan chiqdingiz.', 'info')
    return redirect(url_for('web.index'))


@admin_bp.route('/admin')
@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0

    total_orders = Order.query.count()
    new_orders = Order.query.filter_by(status='new').count()
    total_portfolio = Portfolio.query.count()

    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    top_posts = Post.query.filter_by(is_published=True).order_by(Post.views.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_posts=total_posts,
                           published_posts=published_posts,
                           total_views=total_views,
                           total_orders=total_orders,
                           new_orders=new_orders,
                           total_portfolio=total_portfolio,
                           recent_posts=recent_posts,
                           top_posts=top_posts)

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.settings import Settings
from app.models.user import User
from werkzeug.security import generate_password_hash

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        keys = ['business_name', 'business_address', 'business_city', 'business_state',
                'business_pin', 'business_mobile', 'business_email', 'business_gst',
                'default_jar_rate', 'jar_warning_threshold', 'gst_percent']
        for k in keys:
            val = request.form.get(k, '').strip()
            Settings.set(k, val)
        flash('Settings saved!', 'success')
        return redirect(url_for('settings.index'))
    settings = {s.key: s.value for s in Settings.query.all()}
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm = request.form.get('confirm_password')
    if not current_user.check_password(current):
        flash('Current password is incorrect.', 'danger')
    elif new_pw != confirm:
        flash('New passwords do not match.', 'danger')
    elif len(new_pw) < 6:
        flash('Password must be at least 6 characters.', 'danger')
    else:
        current_user.set_password(new_pw)
        db.session.commit()
        flash('Password changed successfully!', 'success')
    return redirect(url_for('settings.index'))

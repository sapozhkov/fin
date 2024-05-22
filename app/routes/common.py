from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user, logout_user
from app.models import User
from config import Config

bp = Blueprint('common', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    if request.method == 'POST':
        password = request.form.get('password')
        if password == Config.PASSWORD:
            user = User()
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid password.')
    return render_template('login.html')


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('common.login'))

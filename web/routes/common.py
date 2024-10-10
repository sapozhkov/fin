import os
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user, logout_user

from app.plot import PlotBalance
from app.models import User
from app.config import AppConfig

bp = Blueprint('common', __name__)

LOG_FILE = f"{AppConfig.BASE_DIR}/log/login_attempts.log"


def log_failed_attempt(password):
    with open(LOG_FILE, 'a') as log:
        log.write(f'{datetime.now()}, {password}\n')


def is_locked():
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, 'r') as log:
        attempts = log.readlines()
        return len(attempts) >= 300


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        if is_locked():
            flash('Account locked due to too many failed login attempts. Try again later.')
            return redirect(url_for('common.login'))

        password = request.form.get('password')
        if password == AppConfig.PASSWORD:
            user = User()
            login_user(user)
            open(LOG_FILE, 'w').close()
            return redirect(url_for('admin.index'))
        else:
            log_failed_attempt(password)
            flash('Invalid password.')
    return render_template('login.html')


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('common.login'))


@bp.route('/img/acc_balance_chart/<int:acc_run_id>')
def img_balance_chart(acc_run_id):
    return PlotBalance.draw_web(acc_run_id)

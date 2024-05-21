from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Deal, Run
from app.forms.deal_form import DealForm

bp = Blueprint('deals', __name__, url_prefix='/deals')


@bp.route('/')
def index():
    deals = Deal.query.all()
    return render_template('deals/index.html', deals=deals)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    form = DealForm()
    form.run.choices = [(run.id, run.config) for run in Run.query.all()]
    if form.validate_on_submit():
        deal = Deal(
            run=form.run.data,
            type=form.type.data,
            datetime=form.datetime.data,
            price=form.price.data,
            commission=form.commission.data,
            total=form.total.data,
            count=form.count.data
        )
        db.session.add(deal)
        db.session.commit()
        flash('Deal created successfully.')
        return redirect(url_for('deals.index'))
    return render_template('deals/create.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    deal = Deal.query.get_or_404(id)
    form = DealForm(obj=deal)
    form.run.choices = [(run.id, run.config) for run in Run.query.all()]
    if form.validate_on_submit():
        deal.run = form.run.data
        deal.type = form.type.data
        deal.datetime = form.datetime.data
        deal.price = form.price.data
        deal.commission = form.commission.data
        deal.total = form.total.data
        deal.count = form.count.data
        db.session.commit()
        flash('Deal updated successfully.')
        return redirect(url_for('deals.index'))
    return render_template('deals/edit.html', form=form)


@bp.route('/<int:id>')
def view(id):
    deal = Deal.query.get_or_404(id)
    return render_template('deals/view.html', deal=deal)


@bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    deal = Deal.query.get_or_404(id)
    db.session.delete(deal)
    db.session.commit()
    flash('Deal deleted successfully.')
    return redirect(url_for('deals.index'))

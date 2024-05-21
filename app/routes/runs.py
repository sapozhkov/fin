from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Run, Instrument
from app.forms.run_form import RunForm
from lib.time_helper import TimeHelper

bp = Blueprint('runs', __name__, url_prefix='/runs')


@bp.route('/')
def index():
    runs = Run.query.all()
    return render_template('runs/index.html', runs=runs)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    form = RunForm()
    form.instrument.choices = [(instr.id, instr.ticker) for instr in Instrument.query.all()]
    if form.validate_on_submit():
        run = Run(
            instrument=form.instrument.data,
            date=TimeHelper.to_datetime(form.date.data).date(),
            status=form.status.data,
            exit_code=form.exit_code.data,
            last_error=form.last_error.data,
            total=form.total.data,
            depo=form.depo.data,
            profit=form.profit.data,
            data=form.data.data,
            config=form.config.data,
            start_cnt=form.start_cnt.data,
            end_cnt=form.end_cnt.data,
            candle=form.candle.data
        )
        db.session.add(run)
        db.session.commit()
        flash('Run created successfully.')
        return redirect(url_for('runs.index'))
    return render_template('runs/create.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    run = Run.query.get_or_404(id)
    form = RunForm(obj=run)
    form.instrument.choices = [(instr.id, instr.ticker) for instr in Instrument.query.all()]
    if form.validate_on_submit():
        run.instrument = form.instrument.data
        run.date = TimeHelper.to_datetime(form.date.data).date()
        run.status = form.status.data
        run.exit_code = form.exit_code.data
        run.last_error = form.last_error.data
        run.total = form.total.data
        run.depo = form.depo.data
        run.profit = form.profit.data
        run.data = form.data.data
        run.config = form.config.data
        run.start_cnt = form.start_cnt.data
        run.end_cnt = form.end_cnt.data
        run.candle = form.candle.data
        db.session.commit()
        flash('Run updated successfully.')
        return redirect(url_for('runs.index'))
    return render_template('runs/edit.html', form=form)


@bp.route('/<int:id>')
def view(id):
    run = Run.query.get_or_404(id)
    return render_template('runs/view.html', run=run)


@bp.route('/<int:id>/delete')
def delete(id):
    run = Run.query.get_or_404(id)
    db.session.delete(run)
    db.session.commit()
    flash('Run deleted successfully.')
    return redirect(url_for('runs.index'))

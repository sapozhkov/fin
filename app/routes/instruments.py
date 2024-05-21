from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Instrument
from app.forms.instrument_form import InstrumentForm

bp = Blueprint('instruments', __name__, url_prefix='/instruments')


@bp.route('/')
def index():
    instruments = Instrument.query.all()
    return render_template('instruments/index.html', instruments=instruments)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    form = InstrumentForm()
    if form.validate_on_submit():
        instrument = Instrument(
            ticker=form.ticker.data,
            server=form.server.data,
            config=form.config.data,
            status=form.status.data
        )
        db.session.add(instrument)
        db.session.commit()
        flash('Instrument created successfully.')
        return redirect(url_for('instruments.index'))
    return render_template('instruments/create.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    instrument = Instrument.query.get_or_404(id)
    form = InstrumentForm(obj=instrument)
    if form.validate_on_submit():
        instrument.ticker = form.ticker.data
        instrument.server = form.server.data
        instrument.config = form.config.data
        instrument.status = form.status.data
        db.session.commit()
        flash('Instrument updated successfully.')
        return redirect(url_for('instruments.index'))
    return render_template('instruments/edit.html', form=form)


@bp.route('/<int:id>')
def view(id):
    instrument = Instrument.query.get_or_404(id)
    return render_template('instruments/view.html', instrument=instrument)


@bp.route('/<int:id>/delete')
def delete(id):
    instrument = Instrument.query.get_or_404(id)
    db.session.delete(instrument)
    db.session.commit()
    flash('Instrument deleted successfully.')
    return redirect(url_for('instruments.index'))

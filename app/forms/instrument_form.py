from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired


class InstrumentForm(FlaskForm):
    ticker = StringField('Ticker', validators=[DataRequired()])
    server = IntegerField('Server', validators=[DataRequired()])
    config = StringField('Config', validators=[DataRequired()])
    status = IntegerField('Status', validators=[DataRequired()])
    submit = SubmitField('Submit')

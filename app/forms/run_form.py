from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired


class RunForm(FlaskForm):
    instrument = SelectField('Instrument', coerce=int, validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()])
    status = IntegerField('Status', validators=[DataRequired()])
    exit_code = IntegerField('Exit Code', validators=[DataRequired()])
    last_error = StringField('Last Error')
    total = FloatField('Total', validators=[DataRequired()])
    depo = FloatField('Depo', validators=[DataRequired()])
    profit = FloatField('Profit', validators=[DataRequired()])
    data = TextAreaField('Data')
    config = StringField('Config', validators=[DataRequired()])
    start_cnt = IntegerField('Start Count', validators=[DataRequired()])
    end_cnt = IntegerField('End Count', validators=[DataRequired()])
    candle = StringField('Candle', validators=[DataRequired()])
    submit = SubmitField('Submit')

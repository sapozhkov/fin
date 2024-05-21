from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired


class DealForm(FlaskForm):
    run = SelectField('Run', coerce=int, validators=[DataRequired()])
    type = IntegerField('Type', validators=[DataRequired()])
    datetime = StringField('Datetime')
    price = FloatField('Price', validators=[DataRequired()])
    commission = FloatField('Commission', validators=[DataRequired()])
    total = FloatField('Total', validators=[DataRequired()])
    count = IntegerField('Count', validators=[DataRequired()])
    submit = SubmitField('Submit')

from app import db


class AccRunBalance(db.Model):
    __tablename__ = 'acc_run_balance'

    id = db.Column(db.Integer, primary_key=True)
    acc_run = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Float)
    datetime = db.Column(db.DateTime)

    def __repr__(self):
        return f'<AccRunBalance {self.datetime} {self.balance}>'

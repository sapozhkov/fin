from app import db


class AccRunBalance(db.Model):
    __tablename__ = 'acc_run_balance'

    id = db.Column(db.Integer, primary_key=True)
    acc_run = db.Column(db.Integer, db.ForeignKey('acc_runs.id', name='fk_acc_run_balance_acc_run'), nullable=False)
    balance = db.Column(db.Float)
    datetime = db.Column(db.DateTime)

    acc_run_rel = db.relationship('AccRun')

    def __repr__(self):
        return f'<AccRunBalance {self.datetime} {self.balance}>'

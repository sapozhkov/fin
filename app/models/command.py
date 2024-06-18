from app import db
from datetime import datetime, timezone


class Command(db.Model):
    __tablename__ = 'commands'

    id = db.Column(db.Integer, primary_key=True)
    bot_type = db.Column(db.Integer, nullable=False)
    com_type = db.Column(db.Integer, nullable=False)
    run_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.String)
    status = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    expired_at = db.Column(db.DateTime, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('idx_bot_run_status', 'bot_type', 'run_id', 'status'),
    )

    def __repr__(self):
        return f'<Command {self.id} run_id={self.run_id} status={self.status}>'

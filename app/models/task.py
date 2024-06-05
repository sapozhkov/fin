from datetime import datetime, UTC
from typing import Optional

from app import db
from app.constants import TaskStatus


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, nullable=False, default=0, index=True)
    type = db.Column(db.Integer, nullable=False, default=0, index=True)
    name = db.Column(db.String, nullable=False, index=True)
    data = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    def save(self):
        db.session.add(self)
        db.session.commit()

    def already_exists(self):
        closed_statuses = TaskStatus.get_closed_statuses()
        return db.session.query(db.exists().where(
            (Task.type == self.type) & (Task.name == self.name) & (~Task.status.in_(closed_statuses)))
        ).scalar()

    @classmethod
    def get_next(cls) -> Optional['Task']:
        return cls.query.filter(cls.status == TaskStatus.PENDING).order_by(cls.id).first()

    def __repr__(self):
        return f'<Task {self.name} (Status: {self.status}, Type: {self.type})>'

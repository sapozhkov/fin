from datetime import datetime, UTC, timedelta
from typing import Optional

from app import db
from app.constants import TaskStatus


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, nullable=False, default=0, index=True)
    class_name = db.Column(db.String, nullable=False, index=True)
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
            (Task.class_name == self.class_name) & (Task.name == self.name) & (~Task.status.in_(closed_statuses)))
        ).scalar()

    @classmethod
    def get_next(cls) -> Optional['Task']:
        return cls.query.filter(cls.status == TaskStatus.PENDING).order_by(cls.id).first()

    @classmethod
    def clear_tasks_by_timeout(cls):
        timeout_threshold = datetime.now(UTC) - timedelta(days=1)

        timed_out_tasks = cls.query.filter(
            cls.status == TaskStatus.IN_PROGRESS,
            cls.updated_at < timeout_threshold
        ).all()

        for task in timed_out_tasks:
            task.status = TaskStatus.FAILED
            task.error = "timeout"

        db.session.commit()

    def capture_task(self):
        if self.status != TaskStatus.PENDING:
            return False

        updated_rows = db.session.query(Task).filter(
            Task.id == self.id,
            Task.updated_at == self.updated_at
        ).update({
            Task.status: TaskStatus.IN_PROGRESS,
        })
        db.session.commit()

        updated = updated_rows > 0

        # дублируем изменение, так как запрос напрямую к базе был.
        # дата изменения не обновлена, если понадобится, то запросить строку из базы
        if updated:
            self.status = TaskStatus.IN_PROGRESS

        return updated

    @classmethod
    def has_tasks_in_progress(cls):
        return cls.query.filter(cls.status == TaskStatus.IN_PROGRESS).count() > 0

    def __repr__(self):
        return f'<Task {self.id} {self.name} (Status: {self.status}, Class: {self.class_name})>'

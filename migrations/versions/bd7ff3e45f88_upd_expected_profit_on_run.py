"""upd expected_profit on run

Revision ID: bd7ff3e45f88
Revises: 4aedecfaed5a
Create Date: 2024-08-27 18:44:57.418573

"""
from alembic import op
import sqlalchemy as sa

from app import db
from app.models import Run, InstrumentLog


# revision identifiers, used by Alembic.
revision = 'bd7ff3e45f88'
down_revision = '4aedecfaed5a'
branch_labels = None
depends_on = None


def upgrade():
    # # Заполнение данных в новом столбце expected_profit
    runs = Run.query.all()
    for run in runs:
        log = InstrumentLog.query.filter_by(
            instrument_id=run.instrument
        ).filter(
            InstrumentLog.updated_at <= run.date
        ).order_by(InstrumentLog.updated_at.desc()).first()

        if log:
            run.expected_profit = log.expected_profit
        else:
            run.expected_profit = None

        db.session.commit()


def downgrade():
    pass

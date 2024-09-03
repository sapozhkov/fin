from flask import url_for
from flask_admin.contrib.sqla.filters import BaseSQLAFilter

from app.models import Instrument


class InstrumentFilter(BaseSQLAFilter):
    def __init__(self, column, term, name=None):
        super().__init__(column, term)
        self.name = name or column
        self.term = term

    def apply(self, query, value, alias=None):
        return query.filter(Instrument.id == value)

    def operation(self):
        return 'equals'

    def __str__(self):
        return f'{self.name}: {self.term}'

    def get_options(self, view):
        return [(i.id, f"{i.name} ({i.account_rel.name})") for i in Instrument.get_for_filter()]

    @classmethod
    def make_runs_rel(cls, instrument_id):
        return url_for("run.index_view", flt1_0=instrument_id)

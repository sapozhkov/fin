from flask_admin.contrib.sqla.filters import BaseSQLAFilter

from app.models import Account


class AccountFilter(BaseSQLAFilter):
    def __init__(self, column, term, name=None):
        super().__init__(column, term)
        self.name = name or column
        self.term = term

    def apply(self, query, value, alias=None):
        return query.filter(self.column == value)

    def operation(self):
        return 'equals'

    def __str__(self):
        return f'{self.name}: {self.term}'

    def get_options(self, view):
        return [(i.id, i.name) for i in Account.get_for_filter()]

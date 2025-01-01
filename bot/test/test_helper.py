from datetime import datetime, timedelta

from app.helper import TimeHelper


class TestHelper:
    @staticmethod
    def get_trade_days_only(end_date: None | str, days_num: int):
        """
        Возвращает список предыдущих будних дней, но только рабочих

        :param end_date: Строка с датой в формате "YYYY-MM-DD".
        :param days_num: Число дней для возврата.
        :return: Список строк с датами предыдущих будних дней.
        """

        if end_date is None:
            # до утра гоняем предыдущий день, а то откинется лишний
            if TimeHelper.trades_are_not_started():
                end_date = TimeHelper.get_previous_date()
            else:
                end_date = TimeHelper.get_current_date()

        current_date = datetime.strptime(end_date, "%Y-%m-%d")
        out = [end_date]

        while len(out) < days_num:
            current_date -= timedelta(days=1)
            if TimeHelper.is_trading_day(current_date):
                out.append(current_date.strftime("%Y-%m-%d"))

        out.reverse()

        return out

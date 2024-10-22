from tinkoff.invest import Quotation, MoneyValue

from .time_helper import TimeHelper


def q2f(quotation: Quotation | MoneyValue, digits=2):
    """Функция для преобразования Quotation в float"""
    return round(quotation.units + quotation.nano * 1e-9, digits)


def f2q(value):
    """Функция для преобразования float в Quotation"""
    units = int(value)
    nano = int(round(value - units, 2) * 1e9)
    return Quotation(units=units, nano=nano)

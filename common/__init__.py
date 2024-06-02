from tinkoff.invest import Quotation, MoneyValue


# Функция для преобразования Quotation в float
def q2f(quotation: Quotation | MoneyValue, digits=2):
    return round(quotation.units + quotation.nano * 1e-9, digits)


# Функция для преобразования float в Quotation
def f2q(value):
    units = int(value)
    nano = int(round(value - units, 2) * 1e9)
    return Quotation(units=units, nano=nano)

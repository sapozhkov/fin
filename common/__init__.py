from tinkoff.invest import Quotation, MoneyValue


# Функция для преобразования Quotation в float
def q2f(quotation: Quotation | MoneyValue, digits=2):
    return round(quotation.units + quotation.nano * 1e-9, digits)

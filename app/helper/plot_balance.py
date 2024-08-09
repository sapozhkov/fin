import matplotlib.pyplot as plt
import io
from flask import Response
from app.models import AccRunBalance


def plot_balance(acc_run_id):
    # Получаем данные для указанного acc_run
    balances = AccRunBalance.query.filter_by(acc_run=acc_run_id).order_by(AccRunBalance.datetime).all()

    # Построение графика
    times = [b.datetime for b in balances]
    values = [b.balance for b in balances]

    plt.figure(figsize=(10, 5))
    plt.plot(times, values, marker='.')
    # plt.title(f'Баланс по AccRun {acc_run_id}')
    # plt.xlabel('Время')
    # plt.ylabel('Баланс')
    plt.grid(True)

    # Сохранение в буфер как PNG
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()  # Закрыть фигуру, чтобы не было утечки памяти
    buf.seek(0)

    # Возвращаем изображение как ответ
    return Response(buf, mimetype='image/png')

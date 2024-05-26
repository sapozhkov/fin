# import multiprocessing
# workers = multiprocessing.cpu_count() * 2 + 1

bind = "0.0.0.0:8000"
workers = 2  # количество воркеров зависит от количества ядер вашего процессора
reload = True

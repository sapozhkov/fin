Для работы на проде
---

yc compute ssh --name **** --folder-id *****

вот так если зацепиться, то коннектимся под пользаком, у которого есть sudo доступ нормально работающий

/etc/nginx/sites-available/your_project
```
server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/your_project/static;
    }
}
```

# добавить файл к выполнению
```shell
sudo ln -s /etc/nginx/sites-available/your_project /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

# статус сервера
```shell
systemctl status nginx.service
```

# логи

```shell
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

# сертификат

```shell
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx
```

## Установка локали

```shell
sudo locale-gen ru_RU.UTF-8
```

# настройка автозапуска

```shell
sudo nano /etc/systemd/system/myapp.service
```

```
[Unit]
Description=Gunicorn instance to serve my Flask application
After=network.target

[Service]
User=sapsan
Group=www-data
WorkingDirectory=/home/sapsan/fin
ExecStart=/home/sapsan/.local/bin/gunicorn -c gunicorn_config.py web_server:app

[Install]
WantedBy=multi-user.target
```

## Ручной запуск сервера

удобно накатке свежих обновлений, когда все разваливается

```shell
/home/sapsan/.local/bin/gunicorn -c gunicorn_config.py web_server:app
```

## База данных

```shell
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo -i -u postgres
```

```psql```

```postgresql
CREATE USER fin_user WITH PASSWORD 'XXX_your_password_XXX';
CREATE DATABASE fin_db;
GRANT ALL PRIVILEGES ON DATABASE fin_db TO fin_user;
\q
```

выходим из пользователя postgres
```shell
exit
```

это уже от имени обычного пользователя в директории проекта 
```shell
pip install psycopg2-binary
```

## cron

```shell
crontab -e
```

```
30 6 * * 1-6 python3 ~/fin/starter.py >> ~/log/starter.log 2>&1
33 15 * * 1-6 python3 ~/fin/task_set_upd_instr.py >> ~/log/task_set.log 2>&1
*/1 * * * * python3 ~/fin/task_worker.py >> ~/log/tasks.log 2>&1
```

sudo systemctl daemon-reload
sudo systemctl start myapp
sudo systemctl enable myapp

# перезапуск (при каждом изменении кода надо делать)
sudo systemctl restart myapp.service
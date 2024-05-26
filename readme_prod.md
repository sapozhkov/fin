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
sudo ln -s /etc/nginx/sites-available/your_project /etc/nginx/sites-enabled
sudo systemctl restart nginx

# статус сервера
systemctl status nginx.service

# логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# сертификат
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx

# настройка автозапуска
sudo nano /etc/systemd/system/myapp.service

```
[Unit]
Description=Gunicorn instance to serve my Flask application
After=network.target

[Service]
User=sapsan
Group=www-data
WorkingDirectory=/home/sapsan/fin
ExecStart=/home/sapsan/.local/bin/gunicorn -c gunicorn_config.py web:app

[Install]
WantedBy=multi-user.target
```

sudo systemctl daemon-reload
sudo systemctl start myapp
sudo systemctl enable myapp

@echo off
title EcoCart Project Launcher
echo [*] 启动 Redis（Docker）...
docker start ecocart-redis-1

timeout /t 3

echo [*] 启动 Celery Worker...
start cmd /k "celery -A EcoCart worker --loglevel=info"

timeout /t 2

echo [*] 启动 Celery Beat...
start cmd /k "celery -A EcoCart beat --loglevel=info"

timeout /t 2

echo [*] 启动 Django 服务...
start cmd /k "python manage.py runserver"

echo [✓] 所有服务已启动！

@echo off
set PYTHONPATH=.
echo Starting Celery Worker...
echo Make sure Redis is running! (e.g. via docker-compose up -d redis)
celery -A app.infra.queue.celery_app worker --loglevel=info --pool=solo
pause
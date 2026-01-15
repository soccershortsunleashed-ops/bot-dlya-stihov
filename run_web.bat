@echo off
set PYTHONPATH=.
python -m uvicorn app.web.main:app --reload --port 8000
pause
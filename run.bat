@echo off
python -m pip install -r requirements.txt >nul 2>&1
python main.py %*

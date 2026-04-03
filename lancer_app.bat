@echo off
cd /d "%~dp0"
echo Demarrage de l'application Vignerons Independants...
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause

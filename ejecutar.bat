@echo on



REM Start Streamlit in background
start "" streamlit run app.py

REM Wait a few seconds to ensure Streamlit starts before Ngrok
timeout /t 5 > nul

REM Start ngrok (adjust the path to where ngrok.exe is)
start "" ngrok.exe http 8501
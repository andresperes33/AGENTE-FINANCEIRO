@echo off
echo Iniciando Agente Financeiro...
echo.

if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo Aplicando migracoes...
python manage.py migrate

echo.
echo Iniciando servidor...
start http://localhost:8000
python manage.py runserver
pause

# Usar a imagem oficial do Python
FROM python:3.11-slim

# Definir variáveis de ambiente para evitar arquivos .pyc e logs bufferizados
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema necessárias para psycopg2 e outras
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o projeto
COPY . /app/

# Coletar arquivos estáticos
RUN python manage.py collectstatic --noinput

# Criar script de inicialização
RUN echo "#!/bin/bash\n\
python manage.py migrate\n\
gunicorn core.wsgi:application --bind 0.0.0.0:8000" > /app/start.sh
RUN chmod +x /app/start.sh

# Expor a porta que o Gunicorn vai rodar
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["/app/start.sh"]

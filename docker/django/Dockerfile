# Usa uma imagem oficial e leve do Python
FROM python:3.11-slim

# Evita que o Python grave arquivos .pyc no disco e força o log no terminal (sem buffer)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências primeiro (otimiza o cache do Docker)
COPY ./api_django/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto Django
COPY ./api_django /app/

# Expõe a porta 8000
EXPOSE 8000

# Comando para iniciar o servidor
# Em produção, recomenda-se usar o gunicorn: CMD ["gunicorn", "api_django.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
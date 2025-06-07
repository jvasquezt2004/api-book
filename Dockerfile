FROM python:3.11-slim

WORKDIR /app

# Instalar uv como gestor de paquetes
RUN pip install uv

# Copiar archivos de requisitos primero para aprovechar la caché de capas de Docker
COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

# Configuración para NLTK
RUN python -c "import nltk; nltk.download('vader_lexicon')"

# Copiar el resto del código
COPY . .

# Exponer el puerto que usa la aplicación
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

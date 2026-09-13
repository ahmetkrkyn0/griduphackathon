FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Sozlesmeler calisma aninda /contracts'a salt okunur baglanir (compose.yaml),
# imaja KOPYALANMAZ: esik/adres degisince yeniden build gerekmesin.
ENV CONTRACTS_DIR=/contracts

EXPOSE 8000
# Fabrika: sozlesmeler uygulama olusurken okunur, /contracts yoksa servis hic kalkmaz.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

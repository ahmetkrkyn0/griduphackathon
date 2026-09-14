FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# DIKKAT: build context repo KOKUDUR (deploy/compose.yaml: context: ..).
# Sebep: merkez dedektor libs/panoalgo icinde yasar, backend/ disindadir ve imaja
# kurulmasi gerekir (TB2 Adim 4). sim/Dockerfile ile ayni desen.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --no-deps: panoalgo yalnizca PyYAML ister ve o zaten requirements.txt'de.
# Boylece backend'in surum kilitleri panoalgo yuzunden oynamaz.
COPY libs/panoalgo /srv/libs/panoalgo
RUN pip install --no-cache-dir --no-deps /srv/libs/panoalgo

COPY backend/app ./app

# Sozlesmeler calisma aninda /contracts'a salt okunur baglanir (compose.yaml),
# imaja KOPYALANMAZ: esik/adres degisince yeniden build gerekmesin.
ENV CONTRACTS_DIR=/contracts

EXPOSE 8000
# Fabrika: sozlesmeler uygulama olusurken okunur, /contracts yoksa servis hic kalkmaz.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

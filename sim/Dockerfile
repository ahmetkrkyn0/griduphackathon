FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# DIKKAT: build context repo KOKUDUR (deploy/compose.sim.yaml: context: ..).
# Sebep: fizik ureteci libs/panoalgo icinde yasar, sim/ disindadir ve imaja kurulur.
COPY sim/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY libs/panoalgo /srv/libs/panoalgo
RUN pip install --no-cache-dir --no-deps /srv/libs/panoalgo

COPY sim/ /srv/

# Sozlesmeler calisma aninda /contracts'a salt okunur baglanir, imaja KOPYALANMAZ:
# esik/adres degisince yeniden build gerekmesin (backend/Dockerfile ile ayni gerekce).
ENV CONTRACTS_DIR=/contracts

CMD ["python", "panosim.py"]

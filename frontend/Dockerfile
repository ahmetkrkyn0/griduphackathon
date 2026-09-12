# Faz 0: statik saglik sayfasi.
# Faz 1'de (TC1) Vite + React build'i eklenecek — asagidaki iki asamali yapi hazir,
# yorumu kaldirip COPY satirlarini degistirmek yeterli.
#
# FROM node:20-alpine AS build
# WORKDIR /app
# COPY package*.json ./
# RUN npm ci
# COPY . .
# RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
# Faz 1: COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# STAGE 1: Compilazione dell'applicazione React (Usa Node.js e pnpm)
FROM node:22-alpine AS build

# Abilitiamo pnpm tramite corepack
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

# Copiamo package.json e pnpm-workspace (se presente)
COPY package.json pnpm-workspace.yaml* pnpm-lock.yaml* ./
RUN pnpm install

# Copiamo tutto il codice sorgente del frontend
COPY . .

# Compiliamo il progetto per la produzione (genera la cartella /dist)
RUN pnpm run build

# STAGE 2: Server Web Nginx Leggero
FROM nginx:alpine

# Installiamo gettext per avere il comando envsubst (sostituzione variabili d'ambiente)
RUN apk add --no-cache gettext

# Copiamo il template di configurazione Nginx (con variabile ${BACKEND_URL})
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Preleviamo i file statici generati nello Stage 1 e li inseriamo nella cartella di Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Esponiamo la porta HTTP standard
EXPOSE 80

# Al runtime: envsubst sostituisce ${BACKEND_URL} nel template e genera il conf definitivo,
# poi avvia Nginx in primo piano.
# Valore default per Docker Compose locale: http://backend:8000 (nome servizio interno)
# In produzione Azure: passare BACKEND_URL=http://<ip-o-hostname-backend>:8000
CMD ["/bin/sh", "-c", \
  "BACKEND_URL=${BACKEND_URL:-http://backend:8000} envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]

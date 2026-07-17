# 1. Utilizziamo l'immagine ufficiale leggera di Python 3.9
FROM python:3.9-slim

# 2. Impostiamo la cartella di lavoro principale nel container
WORKDIR /backend

# 3. Impostiamo alcune variabili d'ambiente utili per Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Installiamo eventuali dipendenze di sistema minime per la compilazione
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiamo e installiamo i requisiti Python
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 6. Scarichiamo il modello linguistico spaCy per l'italiano e pre-carichiamo il SentenceTransformer
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/huggingface \
    python -m spacy download it_core_news_sm && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# 7. Copiamo il resto dell'applicazione backend
COPY ./app ./app

# 8. Esponiamo la porta 8000 utilizzata da FastAPI
EXPOSE 8000

# 9. Comando di avvio del server Uvicorn (in ascolto su tutte le interfacce 0.0.0.0)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

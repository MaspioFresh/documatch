import os
import uuid
from abc import ABC, abstractmethod
from typing import Optional
from fastapi import UploadFile
from azure.storage.blob import BlobServiceClient

# ---------------------------------------------------------------------------
# Servizio Storage — Pattern Dual-Mode (Locale / Azure Blob Storage)
#
# Gestisce il caricamento delle immagini/scansioni degli atti.
# In sviluppo locale: salva i file nella cartella app/static/uploads/ del backend
#   e restituisce un URL relativo (es. http://127.0.0.1:8000/static/uploads/...)
# In produzione Azure: carica i file su Azure Blob Storage (container cloud)
#   e restituisce l'URL pubblico del blob (accessibile da internet)
# ---------------------------------------------------------------------------

class StorageService(ABC):
    @abstractmethod
    def upload_file(self, file: UploadFile, folder: str = "documents") -> str:
        """Carica un file nello storage e restituisce l'URL pubblico di accesso"""
        pass


# --- IMPLEMENTAZIONE 1: Storage locale (sviluppo) ---
# Salva i file sul disco del computer che esegue il backend.
# Funziona grazie al mount degli static files in main.py (/static).
class LocalStorageService(StorageService):
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        # Creiamo la directory di upload se non esiste già
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _generate_unique_filename(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1]
        return f"{uuid.uuid4()}{ext}"

    def upload_file(self, file: UploadFile, folder: str = "documents") -> str:
        if not file.filename:
            raise ValueError("Nome file non valido")
            
        file_name = self._generate_unique_filename(file.filename)
        file_path = os.path.join(self.upload_dir, file_name)
        
        try:
            with open(file_path, "wb") as buffer:
                # Leggiamo a blocchi per non sovraccaricare la memoria
                while content := file.file.read(1024 * 1024):  # 1MB chunks
                    buffer.write(content)
        except Exception as e:
            raise RuntimeError(f"Errore durante il salvataggio del file: {str(e)}")
            
        return f"/static/uploads/{file_name}"


# --- IMPLEMENTAZIONE 2: Azure Blob Storage (produzione) ---
# Carica i file su Azure Blob Storage, il servizio cloud di Microsoft per file binari.
# I blob sono accessibili tramite URL pubblico e scalano automaticamente.
class AzureBlobStorageService(StorageService):
    def __init__(self, connection_string: str, container_name: str = "documatch-container"):
        self.connection_string = connection_string
        self.container_name = container_name

        # Creiamo il client Blob Storage con la connection string Azure
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_client = self.blob_service_client.get_container_client(self.container_name)

        # Creiamo il container su Azure se non esiste ancora e impostiamo l'accesso in lettura pubblico
        try:
            self.container_client.create_container(public_access="blob")
        except Exception:
            pass  # Il container esiste già, va bene

    def upload_file(self, file: UploadFile, folder: str = "documents") -> str:
        # Il "blob name" è il percorso del file dentro il container
        blob_name = f"{folder}/{file.filename}"
        blob_client = self.container_client.get_blob_client(blob_name)

        # Riposizioniamo il cursore (stesso motivo del LocalStorageService)
        file.file.seek(0)

        # Carichiamo il file su Azure con overwrite=True per permettere sostituzioni
        blob_client.upload_blob(file.file, overwrite=True)

        # Restituiamo l'URL pubblico Azure del blob (accessibile da internet)
        return blob_client.url


# ---------------------------------------------------------------------------
# Selezione automatica dell'implementazione a runtime (Dual-Mode)
# ---------------------------------------------------------------------------
AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if AZURE_CONN_STR:
    storage_service = AzureBlobStorageService(connection_string=AZURE_CONN_STR)
    print("Storage Service attivo: Connesso ad Azure Blob Storage.")
else:
    storage_service = LocalStorageService()
    print("Storage Service attivo: Modalità Offline (Local Storage locale).")

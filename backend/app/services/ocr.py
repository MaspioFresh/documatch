import os
import time
from abc import ABC, abstractmethod
from fastapi import UploadFile
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# ---------------------------------------------------------------------------
# Servizio OCR — Pattern Dual-Mode (Offline Mock / Azure AI Document Intelligence)
#
# In sviluppo locale: restituisce testo pre-scritto realistico in italiano
#   in base al nome del file caricato (delibera, autorizzazione, piano...).
#   Simula un'attesa di 1.2 secondi per imitare il tempo di elaborazione reale.
# In produzione Azure: chiama Azure AI Document Intelligence (ex Form Recognizer)
#   che analizza l'immagine e restituisce il testo riconosciuto.
# ---------------------------------------------------------------------------

class OCRService(ABC):
    @abstractmethod
    def estrai_testo(self, file: UploadFile) -> str:
        """Estrae il testo da un'immagine o file PDF"""
        pass


# --- IMPLEMENTAZIONE 1: Mock locale (sviluppo) ---
# Genera testo amministrativo realistico in italiano senza chiamare Azure.
# Il testo varia in base al tipo di documento rilevato dal nome del file.
class LocalMockOCRService(OCRService):
    def estrai_testo(self, file: UploadFile) -> str:
        # Simuliamo il tempo di elaborazione OCR per un'esperienza realistica
        time.sleep(1.2)

        filename = file.filename.lower()

        # Selezioniamo il testo mock in base alla tipologia dell'atto
        if "delibera" in filename:
            return """COMUNE DI DOCUMATCH
DELIBERAZIONE DELLA GIUNTA COMUNALE - N. 104 del 01/06/2026
OGGETTO: Approvazione lavori di manutenzione straordinaria ed adeguamento sismico del plesso scolastico Falcone-Borsellino.
L'anno duemilaventisei, il giorno uno del mese di giugno, presso la sede comunale.
Presiede il Sindaco Mario Rossi.
Assiste il Segretario Comunale.
LA GIUNTA COMUNALE
Visto il progetto definitivo presentato dall'Ufficio Tecnico, redatto dall'Ing. Luigi Bianchi.
Ritenuta la necessità urgente di procedere alla messa in sicurezza degli edifici scolastici comunali.
DELIBERA
1. Di approvare lo stanziamento dei fondi per i lavori di adeguamento sismico del plesso scolastico Falcone-Borsellino.
2. Di demandare all'Ufficio Tecnico e all'Ufficio Edilizia Scolastica gli adempimenti successivi per l'indizione della gara d'appalto.
Letto, confermato e sottoscritto.
Il Sindaco: Mario Rossi
Il Segretario Comunale: dott.ssa Anna Verdi"""

        elif "autorizzazione" in filename:
            return """COMUNE DI DOCUMATCH - SETTORE EDILIZIA PRIVATA
AUTORIZZAZIONE UNICA EDILIZIA N. 89/2026
Rilasciata in data 01/06/2026
Il Dirigente dell'Ufficio Tecnico Comunale.
Vista la domanda presentata in data 10/05/2026 dal Sig. Antonio Neri.
Esaminata la documentazione allegata ed il parere favorevole espresso dall'Ufficio Tecnico.
AUTORIZZA
Il completamento delle opere di ristrutturazione interna e ampliamento volumetrico dell'immobile ad uso civile abitazione situato in via Roma 12.
Le opere dovranno essere eseguite in conformità al progetto approvato e sotto la direzione dell'Ing. Luigi Bianchi.
La presente autorizzazione ha validità di anni tre a decorrere dalla data odierna.
Il Responsabile del Procedimento: ing. Luigi Bianchi
Il Dirigente del Settore: arch. Sofia Neri"""

        elif "piano" in filename or "programma" in filename:
            return """COMUNE DI DOCUMATCH
PIANO DI GOVERNO DEL TERRITORIO (PGT) - ANNO 2026
Documento Programmatico di Sviluppo Urbano Sostenibile.
Approvato con Delibera del Consiglio Comunale N. 12 in data 15/05/2026.
Presentato dall'Assessore all'Urbanistica ed all'Ambiente.
Redatto in collaborazione con l'Ufficio Tecnico Comunale e il Settore Pianificazione Territoriale.
Sintesi Esecutiva delle Linee Guida di Sviluppo:
1. Riqualificazione delle aree industriali dismesse e incentivi per il recupero edilizio senza consumo di suolo.
2. Estensione delle piste ciclabili urbane e potenziamento del trasporto pubblico elettrico locale.
3. Creazione del nuovo parco urbano attrezzato nella zona est della città, gestito dall'Ufficio Ambiente.
Istruttore della pratica: dott.ssa Elena Russo
I firmatari del documento: Sindaco Mario Rossi, Assessore all'Urbanistica dott. Marco Gialli."""

        else:
            # Testo generico per qualsiasi altro tipo di atto
            return f"""COMUNE DI DOCUMATCH - ATTO AMMINISTRATIVO GENERICO
Documento digitalizzato tramite servizio OCR.
File originario: {file.filename}
Data di elaborazione: 01/06/2026
Ufficio di provenienza: Ufficio Protocollo Generale.
Descrizione sintetica: Atto e documentazione interna relativa ad adempimenti burocratici degli uffici comunali.
Il documento contiene disposizioni organizzative interne per l'efficienza dei servizi erogati alla cittadinanza.
Per ulteriori informazioni o dettagli, si prega di fare riferimento all'Ufficio Relazioni con il Pubblico (URP).
Responsabile del procedimento: dott.ssa Chiara Viola.
Sottoscritto in originale dal Dirigente Amministrativo."""


# --- IMPLEMENTAZIONE 2: Azure AI Document Intelligence (produzione) ---
# Usa il servizio Azure per analizzare immagini e PDF e restituire il testo riconosciuto.
# Il modello "prebuilt-document" è pre-addestrato su documenti generici.
class AzureDocumentIntelligenceOCRService(OCRService):
    def __init__(self, key: str, endpoint: str):
        self.key = key
        self.endpoint = endpoint
        # Inizializziamo il client SDK di Azure con le credenziali
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def estrai_testo(self, file: UploadFile) -> str:
        # Riportiamo il cursore all'inizio del file (potrebbe essere stato letto parzialmente)
        file.file.seek(0)
        file_content = file.file.read()

        # Avviamo l'analisi del documento su Azure (operazione asincrona con polling)
        poller = self.client.begin_analyze_document(
            "prebuilt-document",
            document=file_content
        )
        result = poller.result()  # Aspettiamo il completamento dell'analisi

        # Raccogliamo tutte le righe di testo riconosciute da ogni pagina
        testo_estratto = []
        for page in result.pages:
            for line in page.lines:
                testo_estratto.append(line.content)

        return "\n".join(testo_estratto)


# ---------------------------------------------------------------------------
# Selezione automatica dell'implementazione a runtime (Dual-Mode)
# ---------------------------------------------------------------------------
AZURE_OCR_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
AZURE_OCR_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")

if AZURE_OCR_KEY and AZURE_OCR_ENDPOINT:
    ocr_service = AzureDocumentIntelligenceOCRService(key=AZURE_OCR_KEY, endpoint=AZURE_OCR_ENDPOINT)
    print("OCR Service attivo: Connesso ad Azure AI Document Intelligence.")
else:
    ocr_service = LocalMockOCRService()
    print("OCR Service attivo: Modalità Offline (Local OCR Mock italiano).")

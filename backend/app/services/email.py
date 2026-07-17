import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------------------------------------------------------
# Servizio Email — Pattern Dual-Mode (Offline Mock / Azure SMTP)
#
# Questo servizio gestisce l'invio delle email di reset password.
# In sviluppo locale: scrive il contenuto dell'email su un file .txt in mock_emails/
# In produzione Azure: invia l'email reale tramite SMTP (Azure Communication Services)
#
# Il pattern "classe astratta + due implementazioni + scelta a runtime" permette
# di passare dalla modalità offline a quella online semplicemente impostando
# le variabili d'ambiente, senza modificare una sola riga di codice.
# ---------------------------------------------------------------------------

# Classe astratta: definisce il "contratto" che entrambe le implementazioni devono rispettare.
# Chiunque usi email_service sa che avrà sempre il metodo invia_email_reset(),
# indipendentemente da quale implementazione è attiva.
class EmailService(ABC):
    @abstractmethod
    def invia_email_reset(self, destinario_email: str, username: str, token: str) -> None:
        """Invia un'email di ripristino password contenente il link di reset"""
        pass

    @abstractmethod
    def invia_email_invito(self, destinario_email: str, username: str, token: str) -> None:
        """Invia un'email di invito al nuovo utente con il link per impostare la password"""
        pass

    @abstractmethod
    def invia_email_scadenza(self, destinario_email: str, username: str, nome_documento: str, giorni_rimanenti: int) -> None:
        """Invia un avviso di scadenza documento a un amministratore"""
        pass


# --- IMPLEMENTAZIONE 1: Mock locale (sviluppo) ---
# Invece di inviare una vera email (che richiederebbe credenziali SMTP),
# scrive il contenuto su un file .txt nella cartella mock_emails/.
# Il token di reset può essere letto da lì per testare il flusso localmente.
class LocalMockEmailService(EmailService):
    def invia_email_reset(self, destinario_email: str, username: str, token: str) -> None:
        # Creiamo la directory mock_emails/ se non esiste già
        mock_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mock_emails")
        os.makedirs(mock_dir, exist_ok=True)

        file_path = os.path.join(mock_dir, f"reset_{username}.txt")
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{base_url}/#/reset-password?token={token}"
        content = (
            f"A: {destinario_email}\n"
            f"Oggetto: Ripristino Password dell'Account Comunale\n\n"
            f"Gentile {username},\n"
            f"è stata avviata una richiesta di ripristino per il tuo account amministrativo.\n"
            f"Puoi impostare una nuova password visitando il seguente link monouso (valido per 15 minuti):\n\n"
            f"{link}\n\n"
            f"Se non hai richiesto tu questa modifica, puoi ignorare questo messaggio.\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[MOCK EMAIL] Scritta email per {username} a {destinario_email} in {file_path}")

    def invia_email_invito(self, destinario_email: str, username: str, token: str) -> None:
        mock_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mock_emails")
        os.makedirs(mock_dir, exist_ok=True)

        file_path = os.path.join(mock_dir, f"invite_{username}.txt")
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{base_url}/#/reset-password?token={token}"
        content = (
            f"A: {destinario_email}\n"
            f"Oggetto: Benvenuto in DocuMatch - Imposta la tua password\n\n"
            f"Gentile {username},\n"
            f"l'amministratore ha creato un nuovo account per te nel sistema DocuMatch.\n"
            f"Per iniziare a utilizzare il sistema, imposta la tua password personale visitando il seguente link (valido per 2 ore):\n\n"
            f"{link}\n\n"
            f"Benvenuto a bordo!\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[MOCK EMAIL] Scritta email di invito per {username} a {destinario_email} in {file_path}")

    def invia_email_scadenza(self, destinario_email: str, username: str, nome_documento: str, giorni_rimanenti: int) -> None:
        mock_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mock_emails")
        os.makedirs(mock_dir, exist_ok=True)

        file_path = os.path.join(mock_dir, f"scadenza_{username}.txt")
        content = (
            f"A: {destinario_email}\n"
            f"Oggetto: Avviso Scadenza Documento - {nome_documento}\n\n"
            f"Gentile {username},\n"
            f"ti informiamo che il documento '{nome_documento}' scadrà tra esattamente {giorni_rimanenti} giorni.\n"
            f"Accedi al sistema DocuMatch per verificare i dettagli ed eventuali azioni da intraprendere.\n"
        )
        # Append mode per non sovrascrivere se ci sono più email di scadenza nello stesso giorno
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content + "\n----------------------------------------\n")
        print(f"[MOCK EMAIL] Scritta email di scadenza per {username} a {destinario_email} in {file_path}")


# --- IMPLEMENTAZIONE 2: Azure SMTP (produzione) ---
# Invia l'email reale tramite il server SMTP di Azure Communication Services.
# Le credenziali vengono passate nel costruttore (lette dalle variabili d'ambiente).
class AzureSMTPEmailService(EmailService):
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_from_email: str
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_from_email = smtp_from_email

    def invia_email_reset(self, destinario_email: str, username: str, token: str) -> None:
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{base_url}/#/reset-password?token={token}"

        # Costruiamo il messaggio email in formato MIME (standard per le email)
        msg = MIMEMultipart()
        msg["From"] = self.smtp_from_email
        msg["To"] = destinario_email
        msg["Subject"] = "Ripristino Password dell'Account Comunale"

        body = (
            f"Gentile {username},\n"
            f"è stata avviata una richiesta di ripristino per il tuo account amministrativo.\n"
            f"Puoi impostare una nuova password visitando il seguente link monouso (valido per 15 minuti):\n\n"
            f"{link}\n\n"
            f"Se non hai richiesto tu questa modifica, puoi ignorare questo messaggio.\n"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            # Connessione SMTP con STARTTLS: la connessione parte non cifrata
            # poi viene "aggiornata" a TLS per sicurezza (standard Azure)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"[SMTP EMAIL] Email di reset inviata con successo a {destinario_email}")
        except Exception as e:
            # Non blocchiamo l'esecuzione se l'email fallisce:
            # il token è già stato salvato nel DB e l'operazione principale è riuscita.
            # Logghiamo l'errore per diagnostica.
            print(f"[SMTP EMAIL] Errore durante l'invio dell'email a {destinario_email}: {e}")

    def invia_email_invito(self, destinario_email: str, username: str, token: str) -> None:
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{base_url}/#/reset-password?token={token}"

        msg = MIMEMultipart()
        msg["From"] = self.smtp_from_email
        msg["To"] = destinario_email
        msg["Subject"] = "Benvenuto in DocuMatch - Imposta la tua password"

        body = (
            f"Gentile {username},\n"
            f"l'amministratore ha creato un nuovo account per te nel sistema DocuMatch.\n"
            f"Per iniziare a utilizzare il sistema, imposta la tua password personale visitando il seguente link (valido per 2 ore):\n\n"
            f"{link}\n\n"
            f"Benvenuto a bordo!\n"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"[SMTP EMAIL] Email di invito inviata con successo a {destinario_email}")
        except Exception as e:
            print(f"[SMTP EMAIL] Errore durante l'invio dell'email di invito a {destinario_email}: {e}")

    def invia_email_scadenza(self, destinario_email: str, username: str, nome_documento: str, giorni_rimanenti: int) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.smtp_from_email
        msg["To"] = destinario_email
        msg["Subject"] = f"Avviso Scadenza Documento - {nome_documento}"

        body = (
            f"Gentile {username},\n"
            f"ti informiamo che il documento '{nome_documento}' scadrà tra esattamente {giorni_rimanenti} giorni.\n"
            f"Accedi al sistema DocuMatch per verificare i dettagli ed eventuali azioni da intraprendere.\n"
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"[SMTP EMAIL] Email di scadenza inviata con successo a {destinario_email}")
        except Exception as e:
            print(f"[SMTP EMAIL] Errore durante l'invio dell'email di scadenza a {destinario_email}: {e}")


# ---------------------------------------------------------------------------
# Selezione automatica dell'implementazione a runtime (Dual-Mode)
#
# Se le variabili d'ambiente SMTP sono tutte presenti → modalità produzione (Azure SMTP)
# Altrimenti → modalità sviluppo (Mock locale su file)
#
# Tutto il resto del codice usa email_service senza sapere quale è attiva.
# ---------------------------------------------------------------------------
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT_STR = os.getenv("SMTP_PORT", "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

if SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM_EMAIL:
    try:
        smtp_port = int(SMTP_PORT_STR)
    except ValueError:
        smtp_port = 587  # Porta standard SMTP con STARTTLS

    email_service = AzureSMTPEmailService(
        smtp_server=SMTP_SERVER,
        smtp_port=smtp_port,
        smtp_username=SMTP_USERNAME,
        smtp_password=SMTP_PASSWORD,
        smtp_from_email=SMTP_FROM_EMAIL
    )
    print("Email Service attivo: Connesso via SMTP (Azure Communication Services).")
else:
    # Variabili SMTP non configurate → usiamo il mock locale per sviluppo
    email_service = LocalMockEmailService()
    print("Email Service attivo: Modalità Offline (Local Email Mock).")

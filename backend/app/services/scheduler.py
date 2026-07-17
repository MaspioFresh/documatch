from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.services.email import email_service

scheduler = BackgroundScheduler()

def check_expiring_documents(force_all_upcoming: bool = False):
    """
    Controlla i documenti in scadenza.
    Di default (cron) controlla solo quelli a 15, 7 o 1 giorno dalla scadenza per non spammare.
    Se force_all_upcoming=True (usato dal tasto Demo), prende tutti i documenti in scadenza nei prossimi 15 giorni.
    """
    print(f"[{datetime.datetime.now().isoformat()}] Avvio cron job controllo scadenze documenti...")
    db: Session = SessionLocal()
    try:
        oggi = datetime.date.today()
        
        if force_all_upcoming:
            # Modalità Demo: prendiamo tutti i documenti che scadranno nei prossimi 15 giorni (o già scaduti ma vicini)
            target = oggi + datetime.timedelta(days=15)
            documenti_in_scadenza = db.query(Document).filter(
                Document.data_scadenza != None,
                Document.data_scadenza <= target,
                Document.data_scadenza >= oggi
            ).all()
        else:
            # Modalità Cron Normale: avvisiamo a 15, 7 e 1 giorno esatto
            t_15 = oggi + datetime.timedelta(days=15)
            t_7 = oggi + datetime.timedelta(days=7)
            t_1 = oggi + datetime.timedelta(days=1)
            documenti_in_scadenza = db.query(Document).filter(
                Document.data_scadenza.in_([t_15, t_7, t_1])
            ).all()

        if not documenti_in_scadenza:
            print("Nessun documento in scadenza trovato.")
            return

        print(f"Trovati {len(documenti_in_scadenza)} documenti in scadenza. Recupero utenti...")
        
        # Recupera tutti gli utenti per inviare la notifica
        utenti = db.query(User).all()
        
        if not utenti:
            print("Nessun utente a cui inviare notifiche.")
            return

        for doc in documenti_in_scadenza:
            for utente in utenti:
                # Se l'utente non ha email, saltiamo
                if not utente.email:
                    continue
                
                # Calcoliamo i giorni effettivi rimanenti
                giorni_rimanenti = (doc.data_scadenza - oggi).days if doc.data_scadenza else 15
                
                email_service.invia_email_scadenza(
                    destinario_email=utente.email,
                    username=utente.username,
                    nome_documento=doc.nome,
                    giorni_rimanenti=giorni_rimanenti
                )

    except Exception as e:
        print(f"Errore durante l'esecuzione del cron job: {e}")
    finally:
        db.close()
    
    print(f"[{datetime.datetime.now().isoformat()}] Cron job controllo scadenze completato.")

def start_scheduler():
    """Inizializza lo scheduler e aggiunge i cron job."""
    # Esegue il job ogni giorno alle 08:00
    scheduler.add_job(
        check_expiring_documents,
        CronTrigger(hour=8, minute=0),
        id="check_expiring_documents_job",
        replace_existing=True
    )
    scheduler.start()
    print("Background scheduler avviato.")

def shutdown_scheduler():
    """Arresta lo scheduler."""
    scheduler.shutdown()
    print("Background scheduler fermato.")

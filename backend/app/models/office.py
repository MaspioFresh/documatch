from sqlalchemy import Column, Integer, String
from app.core.database import Base

# ---------------------------------------------------------------------------
# Modello Office — Rappresenta un ufficio comunale configurabile
#
# Tabella semplice con solo id e nome. Gli uffici vengono usati come etichette
# nei documenti (campo "uffici") e sono gestibili dall'Amministratore Supremo
# tramite il pannello admin. L'indicizzazione del nome permette ricerche rapide.
# ---------------------------------------------------------------------------
class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, index=True, nullable=False)

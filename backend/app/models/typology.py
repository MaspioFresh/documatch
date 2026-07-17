from sqlalchemy import Column, Integer, String
from app.core.database import Base

# ---------------------------------------------------------------------------
# Modello Typology — Rappresenta una tipologia documentale configurabile
#
# Tabella semplice con solo id e nome. Le tipologie (es. "Delibera di Giunta",
# "Ordinanza Sindacale") sono usate per classificare gli atti e sono gestibili
# dall'Amministratore Supremo. La tipologia "Altro" è protetta da eliminazione:
# i documenti la cui tipologia viene cancellata vengono automaticamente
# riclassificati come "Altro" (vedi crud_entita.py → _propaga_tipologia_elimina).
# ---------------------------------------------------------------------------
class Typology(Base):
    __tablename__ = "typologies"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, index=True, nullable=False)

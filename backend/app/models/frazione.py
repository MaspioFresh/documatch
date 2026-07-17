from sqlalchemy import Column, Integer, String
from app.core.database import Base

# ---------------------------------------------------------------------------
# Modello Frazione — Rappresenta una frazione o zona comunale configurabile
#
# Tabella semplice con solo id e nome. Le frazioni (es. "Capoluogo (Centro)",
# "Frazione Marina") rappresentano le zone geografiche del territorio comunale
# e vengono usate per localizzare gli atti. Gestibili dall'Amministratore Supremo.
# ---------------------------------------------------------------------------
class Frazione(Base):
    __tablename__ = "frazioni"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, index=True, nullable=False)

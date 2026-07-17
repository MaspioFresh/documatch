import json
import numpy as np
import spacy
from collections import Counter
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from app.models.document import Document

# =============================================================================
# Servizio NLP — Elaborazione del linguaggio naturale
#
# Questo modulo è il cuore della ricerca semantica di DocuMatch.
# Usa due librerie distinte per due compiti diversi:
#
#   spaCy (it_core_news_sm) — Named Entity Recognition (NER)
#     Analizza il testo e riconosce automaticamente i nomi di persone,
#     organizzazioni e luoghi (es. estrae "Ufficio Tecnico" e "Mario Rossi"
#     dal testo OCR di un atto senza che nessuno le abbia indicate).
#
#   SentenceTransformer (paraphrase-multilingual-MiniLM-L12-v2) — Embeddings
#     Converte qualsiasi testo in un vettore numerico a 384 dimensioni.
#     Testi con significato simile producono vettori simili nello spazio vettoriale,
#     anche se usano parole diverse. Questo è il cuore della ricerca semantica.
#
# ⚠️ PUNTO CRITICO: entrambi i modelli vengono caricati UNA SOLA VOLTA all'avvio
# del server (non per ogni richiesta). Il caricamento richiede 2-5 secondi e
# ~200MB di RAM, ma poi le singole query impiegano solo pochi millisecondi.
# =============================================================================

# Carichiamo il modello linguistico italiano di spaCy
try:
    nlp = spacy.load("it_core_news_sm")
except OSError:
    # Fallback nel caso in cui non sia installato nel path globale ma come pacchetto Python
    import it_core_news_sm
    nlp = it_core_news_sm.load()

# Carichiamo il modello Transformer multilingua per gli embeddings vettoriali.
# Al primo avvio, scarica automaticamente il modello (~120MB) da HuggingFace.
# Nei run successivi usa la versione in cache locale.
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# =============================================================================
# Stopwords Burocratiche
#
# Set di parole comuni nel linguaggio amministrativo italiano che non aggiungono
# valore semantico alla ricerca (articoli, preposizioni, termini generici degli atti).
# Vengono filtrate durante l'estrazione dei concetti chiave per ridurre il "rumore"
# nei confronti tra documenti.
# =============================================================================
STOPWORDS_BUROCRATICHE = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "e", "o", "ma", "che", "del", "dello",
    "della", "dei", "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle", "nel", "nello", "nella",
    "nei", "negli", "nelle", "col", "coi", "sul", "sulla", "sugli", "sulle",
    "ed", "ad", "non", "sono", "è", "era", "erano", "stato", "stata", "stati",
    "state", "anche", "come", "questo", "questa", "questi", "queste", "quello",
    "quella", "quelli", "quelle", "n", "n.", "numero", "delibera", "determina",
    "ordinanza", "atto", "comune", "comunale", "dirigenziale", "sindacale",
    "sotto", "sopra", "perché", "quindi", "all", "sull", "deliberazione",
    "determinazione", "decreto", "provvedimento", "provvedimenti", "ufficio",
    "uffici", "servizio", "servizi", "settore", "sindaco", "dirigente",
    "giunta", "consiglio", "responsabile", "responsabili", "approvazione",
    "approvare", "previsione", "preparazione", "adozione", "misura", "misure",
    "articolo", "art", "legge", "regolamento", "anno", "data", "giorno", "mese",
    "comunali", "oggetto", "relativo", "relativi", "relativa", "relative",
    "inerente", "inerenti", "riguardante", "riguardanti", "definizione", "definitivo"
}

# =============================================================================
# _estrai_lemmi_e_forme — Helper NLP condiviso
#
# Dato un documento già analizzato da spaCy, estrae un dizionario
# {lemma: forma_più_comune} per i sostantivi, nomi propri e aggettivi.
# Il lemma è la forma "radice" della parola (es. "manutenzione" → "manutenzione"),
# la forma è come appare effettivamente nel testo.
# Il risultato è ordinato per frequenza decrescente (i concetti più ripetuti prima).
# =============================================================================
def _estrai_lemmi_e_forme(doc_parsed):
    """
    Estrae lemmi e la forma originale più comune da un documento spaCy,
    ordinati per frequenza decrescente.
    """
    lemmi = {}
    for token in doc_parsed:
        lemma = token.lemma_.lower().strip()
        # Prendiamo solo sostantivi (NOUN), nomi propri (PROPN) e aggettivi (ADJ)
        # con lemma di almeno 4 caratteri e non tra le stopwords burocratiche
        if (token.pos_ in ["NOUN", "PROPN", "ADJ"]
            and len(lemma) > 3
            and lemma not in STOPWORDS_BUROCRATICHE
            and not token.is_digit):
            originale = token.text.strip()
            if lemma not in lemmi:
                lemmi[lemma] = []
            lemmi[lemma].append(originale)

    # Ordiniamo per frequenza decrescente: i concetti più ripetuti vengono prima
    sorted_lemmi = sorted(lemmi.items(), key=lambda item: len(item[1]), reverse=True)
    best_forme = {}
    for lemma, forme in sorted_lemmi:
        c = Counter(forme)
        # Per ogni lemma prendiamo la forma più usata nel testo
        best_forme[lemma] = c.most_common(1)[0][0]
    return best_forme


def _ottieni_lista(campo):
    """Deserializza un campo che può essere una lista Python, una stringa JSON o CSV."""
    if not campo:
        return []
    if isinstance(campo, list):
        return campo
    try:
        return json.loads(campo)
    except Exception:
        return [x.strip() for x in campo.split(",") if x.strip()]


def _ottieni_principali_sostantivi(lemmi_dict, count=2):
    """Estrae le prime `count` forme leggibili da un dizionario lemmi (per le spiegazioni testuali)."""
    return [f"'{forme}'" for _lemma, forme in list(lemmi_dict.items())[:count]]


def _formatta_punti(punti_condivisi: list) -> str:
    """Unisce una lista di punti con virgole e 'e' prima dell'ultimo (stile italiano)."""
    if len(punti_condivisi) > 1:
        return ", ".join(punti_condivisi[:-1]) + f" e {punti_condivisi[-1]}"
    return punti_condivisi[0]


# =============================================================================
# elabora_testo_nlp — Named Entity Recognition (NER)
#
# Analizza il testo estratto dall'OCR con la pipeline spaCy e identifica
# automaticamente le entità rilevanti per i metadati del documento:
#   - PER (Person) → Firmatari e funzionari nominati nel documento
#   - ORG/LOC      → Uffici, enti o luoghi citati nel testo
#
# ⚠️ PUNTO CRITICO: spaCy non è perfetto (può sbagliare il tipo di entità),
# ma è abbastanza preciso da ridurre drasticamente il lavoro manuale del
# funzionario che deve compilare i metadati dell'atto.
# =============================================================================
def elabora_testo_nlp(testo: str) -> Tuple[List[str], List[str]]:
    """
    Analizza il testo ed estrae automaticamente le entità nominative (firmatari e uffici)
    usando la pipeline di Named Entity Recognition (NER) di spaCy.

    Ritorna: (lista_uffici, lista_firmatari)
    """
    if not testo:
        return [], []

    doc = nlp(testo)
    firmatari = []
    uffici = []

    for ent in doc.ents:
        # PER (Person): nomi di persone fisiche → diventano firmatari
        if ent.label_ == "PER":
            nome_pulito = ent.text.strip()
            if nome_pulito and nome_pulito not in firmatari:
                firmatari.append(nome_pulito)
        # ORG (Organization) o LOC (Location): uffici, enti, luoghi → diventano uffici
        elif ent.label_ in ["ORG", "LOC"]:
            ufficio_pulito = ent.text.strip()
            if ufficio_pulito and ufficio_pulito not in uffici:
                uffici.append(ufficio_pulito)

    return uffici, firmatari


# =============================================================================
# clean_and_stem — Stemming personalizzato per l'italiano
#
# Normalizza le parole rimuovendo suffissi morfologici comuni in italiano:
# plurali, desinenze verbali, suffissi aggettivali.
# Questo permette alla ricerca ibrida di trovare corrispondenze tra parole
# con la stessa radice lessicale (es. "manutenzione" e "manutenzioni"
# producono entrambe la radice "manutenzi-").
#
# ⚠️ NON è lo stesso del lemmatizzatore di spaCy: è più aggressivo e
# progettato specificamente per massimizzare il recall nella ricerca.
# =============================================================================
def clean_and_stem(word: str) -> str:
    """
    Rimuove caratteri non alfanumerici ed esegue lo stemming personalizzato
    per mappare parole morfologicamente correlate in italiano alla stessa radice.
    """
    word = word.lower().strip()
    word = "".join([c for c in word if c.isalnum()])
    if not word:
        return ""

    consonants = set("bcdfghlmnpqrstvz")
    # Rimuoviamo il prefisso 's' seguito da consonante (es. "sfalcio" → "falcio")
    if len(word) > 4 and word.startswith("s") and word[1] in consonants:
        word = word[1:]

    # Lista dei suffissi da rimuovere, in ordine dal più lungo al più corto
    # (questo garantisce che vengano applicati in modo greedy)
    suffixes = [
        "azione", "zioni", "mente", "menti", "mento", "atura", "ature", "tore", "trice",
        "ando", "endo", "ante", "ente", "asse", "esse", "isse",
        "ano", "ate", "ete", "ite", "ato", "uto", "ito", "are", "ere", "ire",
        "ico", "ica", "ici", "iche", "oso", "osa", "osi", "ose",
        "o", "a", "e", "i"
    ]
    for suf in suffixes:
        # Applichiamo solo se la radice risultante ha almeno 3 caratteri
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[:-len(suf)]
    return word


# =============================================================================
# genera_embedding — Codifica vettoriale del testo
#
# Converte una stringa di testo in un vettore denso a 384 dimensioni usando
# il modello SentenceTransformer multilingua.
#
# ⚠️ PUNTO CRITICO: 384 dimensioni è il compromesso scelto dal modello tra
# precisione (più dimensioni = più espressivo) e velocità (più dimensioni = più lento).
# Il vettore viene salvato nel DB come stringa JSON e deserializzato ad ogni ricerca.
# =============================================================================
def genera_embedding(testo: str) -> List[float]:
    """
    Genera la rappresentazione vettoriale densa (embedding a 384 dimensioni)
    del testo fornito tramite il modello SentenceTransformer multilingua.
    """
    if not testo:
        # Vettore nullo di default per testo vuoto
        return [0.0] * 384

    # encode() restituisce un numpy array: lo convertiamo in lista di float standard
    vector = embedding_model.encode(testo)
    return vector.tolist()


# =============================================================================
# calcola_similarita_coseno — Metrica di affinità vettoriale
#
# Misura la similarità direzionale tra due vettori semantici.
# Il coseno dell'angolo tra i due vettori nello spazio a 384 dimensioni:
#   1.0  = vettori identici (stessa direzione)
#   0.0  = vettori ortogonali (nessuna relazione semantica)
#  -1.0  = vettori opposti (significati opposti, raro in pratica)
#
# Formula: similarity = (A · B) / (||A|| × ||B||)
# =============================================================================
def calcola_similarita_coseno(vettore_a: List[float], vettore_b: List[float]) -> float:
    """
    Calcola il punteggio di similarità coseno tra due vettori semantici.
    Restituisce un valore tra -1.0 e 1.0 (1.0 = massima affinità semantica).
    """
    arr_a = np.array(vettore_a)
    arr_b = np.array(vettore_b)

    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0  # Uno dei due è il vettore nullo: similarità zero per definizione

    # Prodotto scalare diviso per il prodotto delle norme = coseno dell'angolo
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


# =============================================================================
# cerca_documenti_simili — Ricerca vettoriale ibrida
#
# Scorre tutti i documenti con embedding nel DB e calcola la similarità coseno
# con il vettore della query. Applica anche un "boost" basato su stem overlap:
# se la query condivide parole con la stessa radice del documento, il punteggio
# viene incrementato per privilegiare la corrispondenza lessicale diretta.
#
# Questo approccio "ibrido" (semantico + lessicale) è più preciso del solo
# embedding quando la query contiene termini tecnici specifici.
#
# Restituisce i `limite` documenti più rilevanti, ordinati per score decrescente.
# =============================================================================
def cerca_documenti_simili(
    vettore_query: List[float],
    tutti_i_documenti: List[Document],
    limite: int = 3,
    query_testo: Optional[str] = None
) -> List[Tuple[Document, float]]:
    """
    Confronta il vettore di ricerca con gli embeddings di tutti i documenti in database,
    restituendo i documenti più simili ordinati per punteggio decrescente.
    Supporta la ricerca ibrida tramite keyword/stem boosting se query_testo è fornito.
    """
    risultati = []

    # Pre-elaborazione per la ricerca ibrida: calcoliamo le radici (stems) delle parole della query
    query_words = []
    query_stems = set()
    if query_testo:
        query_words = [w.lower().strip() for w in query_testo.split() if len(w) > 2]
        query_stems = {clean_and_stem(w) for w in query_words if clean_and_stem(w)}

    for doc in tutti_i_documenti:
        if not doc.embedding:
            continue  # Documento senza embedding: non può essere cercato semanticamente

        try:
            # Deserializziamo il vettore del documento (salvato come stringa JSON nel DB)
            doc_vector = json.loads(doc.embedding)
            score = calcola_similarita_coseno(vettore_query, doc_vector)

            # Boost ibrido: se ci sono corrispondenze di stem tra query e documento,
            # incrementiamo il punteggio per privilegiare i documenti lessicalmente pertinenti
            if query_testo and query_stems:
                doc_text = f"{doc.nome} {doc.descrizione or ''} {doc.testo_estratto or ''}".lower()
                doc_words = [w for w in doc_text.split() if len(w) > 2]
                doc_stems = {clean_and_stem(w) for w in doc_words if clean_and_stem(w)}

                # Troviamo gli stem in comune tra query e documento (con tolleranza per substring)
                overlap = set()
                for qs in query_stems:
                    for ds in doc_stems:
                        if qs == ds:
                            overlap.add(qs)
                        elif (qs in ds or ds in qs) and min(len(qs), len(ds)) >= 4:
                            overlap.add(qs if len(qs) < len(ds) else ds)

                boost = 0.0
                if overlap:
                    boost += 0.22 * len(overlap)   # +22% per ogni stem in comune
                    exact_overlap = set(query_words).intersection(set(doc_words))
                    if exact_overlap:
                        boost += 0.10 * len(exact_overlap)  # +10% per ogni parola esatta in comune

                score += boost

            # Escludiamo risultati con affinità troppo bassa (rumore)
            if score > 0.1:
                risultati.append((doc, score))
        except Exception:
            continue  # Se il vettore è corrotto, saltiamo il documento

    # Ordiniamo per score decrescente e prendiamo i migliori `limite`
    risultati.sort(key=lambda x: x[1], reverse=True)
    return risultati[:limite]


# =============================================================================
# spiega_similarita_semantica — Spiegazione AI per raccomandazioni
#
# Genera una frase esplicativa in italiano della correlazione tra due atti.
# Funziona in due modalità:
#   1. Azure OpenAI: genera una spiegazione ricca e naturale (se configurato)
#   2. Fallback locale: analizza con spaCy i concetti, uffici, firmatari e
#      frazioni in comune tra i due documenti e costruisce una frase descrittiva
#
# Usata nel pannello "Atti Correlati" nella modale di dettaglio.
# =============================================================================
def spiega_similarita_semantica(doc1: Document, doc2: Document, score: float) -> str:
    """
    Analizza i testi e i metadati dei due documenti ed elabora una spiegazione
    in italiano dell'affinità semantica calcolata.
    """
    # Prima tentiamo con Azure OpenAI per una risposta più naturale
    from app.services.generative_ai import genera_spiegazione_azure_openai_correlazione
    spiegazione_llm = genera_spiegazione_azure_openai_correlazione(
        doc1.nome, doc1.descrizione or doc1.testo_estratto,
        doc2.nome, doc2.descrizione or doc2.testo_estratto
    )
    if spiegazione_llm:
        return spiegazione_llm

    # Fallback locale: costruiamo la spiegazione analizzando i metadati
    parsed1 = nlp(f"{doc1.nome}. {doc1.descrizione or ''}")
    parsed2 = nlp(f"{doc2.nome}. {doc2.descrizione or ''}")

    lemmi1 = _estrai_lemmi_e_forme(parsed1)
    lemmi2 = _estrai_lemmi_e_forme(parsed2)
    comuni_lemmi = set(lemmi1.keys()) & set(lemmi2.keys())  # Concetti chiave in comune

    uffici_comuni = set(_ottieni_lista(doc1.uffici)) & set(_ottieni_lista(doc2.uffici))
    firmatari_comuni = set(_ottieni_lista(doc1.firmatari)) & set(_ottieni_lista(doc2.firmatari))
    frazioni_comuni = set(_ottieni_lista(doc1.frazioni)) & set(_ottieni_lista(doc2.frazioni))

    punti_condivisi = []

    if comuni_lemmi:
        parole = [f"'{lemmi1[l]}'" for l in list(comuni_lemmi)[:4]]
        punti_condivisi.append(
            f"al concetto chiave di {parole[0]}" if len(parole) == 1
            else f"ai concetti chiave di {', '.join(parole[:-1])} e {parole[-1]}"
        )
    if uffici_comuni:
        uff = [f"'{u}'" for u in list(uffici_comuni)[:2]]
        punti_condivisi.append(
            f"al coinvolgimento dell'ufficio {uff[0]}" if len(uff) == 1
            else f"al coinvolgimento degli uffici {', '.join(uff[:-1])} e {uff[-1]}"
        )
    if firmatari_comuni:
        firm = [f"'{f}'" for f in list(firmatari_comuni)[:2]]
        punti_condivisi.append(
            f"alla sottoscrizione di {firm[0]}" if len(firm) == 1
            else f"alle firme congiunte di {', '.join(firm[:-1])} e {firm[-1]}"
        )
    if frazioni_comuni:
        fraz = [f"'{f}'" for f in list(frazioni_comuni)[:2]]
        punti_condivisi.append(
            f"alla localizzazione presso la medesima frazione o zona ({fraz[0]})" if len(fraz) == 1
            else f"alla localizzazione presso le frazioni o zone {', '.join(fraz[:-1])} e {fraz[-1]}"
        )

    stessa_tipologia = doc1.tipologia.lower() == doc2.tipologia.lower()
    percentuale = int(round(score * 100))

    if punti_condivisi:
        dettaglio = _formatta_punti(punti_condivisi)
        if stessa_tipologia:
            return f"Entrambi gli atti sono classificati come '{doc1.tipologia}' ed includono forti correlazioni tematiche relative {dettaglio}."
        return f"Nonostante la differente tipologia ({doc1.tipologia} e {doc2.tipologia}), entrambi gli atti condividono tematiche relative {dettaglio}."

    # Fallback finale: descrizione generica basata sui sostantivi principali
    sost1 = _ottieni_principali_sostantivi(lemmi1)
    sost2 = _ottieni_principali_sostantivi(lemmi2)
    contesto1 = f"tratta tematiche legate a {', '.join(sost1)}" if sost1 else "riguarda il primo atto"
    contesto2 = f"si focalizza su {', '.join(sost2)}" if sost2 else "il secondo atto"

    if stessa_tipologia:
        return f"Entrambi gli atti sono di tipo '{doc1.tipologia}' ed operano nello stesso alveo amministrativo. Pur con sfumature diverse ({contesto1} e {contesto2}), condividono un'affinità semantica del {percentuale}% basata su contesti operativi correlati dell'ente."
    return f"Gli atti condividono un'affinità concettuale indiretta del {percentuale}%. Il primo {contesto1}, mentre il secondo {contesto2}, incrociandosi nel medesimo disegno di gestione ed erogazione dei servizi comunali."


# =============================================================================
# spiega_similarita_ricerca — Spiegazione AI per risultati di ricerca
#
# Come spiega_similarita_semantica ma confronta la QUERY dell'utente (non un documento)
# con il documento trovato. Identifica le corrispondenze in: tipologia, concetti chiave,
# uffici, firmatari, frazione, per spiegare al cittadino perché quell'atto è rilevante.
#
# Usata nella lista dei risultati della tab di ricerca.
# =============================================================================
def spiega_similarita_ricerca(query_testo: str, doc: Document, score: float) -> str:
    """
    Spiega quali elementi della ricerca del cittadino corrispondono all'atto trovato.
    Priorità: Azure OpenAI > fallback locale con spaCy.
    """
    # Prima tentiamo con Azure OpenAI
    from app.services.generative_ai import genera_spiegazione_azure_openai_ricerca
    spiegazione_llm = genera_spiegazione_azure_openai_ricerca(
        query_testo, doc.nome, doc.descrizione or doc.testo_estratto
    )
    if spiegazione_llm:
        return spiegazione_llm

    # Fallback locale: analisi con spaCy
    parsed_query = nlp(query_testo)
    parsed_doc = nlp(f"{doc.nome}. {doc.descrizione or ''}")

    lemmi_query = _estrai_lemmi_e_forme(parsed_query)
    lemmi_doc = _estrai_lemmi_e_forme(parsed_doc)

    # Troviamo le parole del documento che "matchano" per stem con la query
    query_words_clean = [t.text.strip() for t in parsed_query if len(t.text.strip()) > 2 and t.text.lower() not in STOPWORDS_BUROCRATICHE]
    doc_words_clean = [t.text.strip() for t in parsed_doc if len(t.text.strip()) > 2 and t.text.lower() not in STOPWORDS_BUROCRATICHE]

    query_stems_map = {clean_and_stem(w): w for w in query_words_clean if clean_and_stem(w)}
    doc_stems_map = {}
    for w in doc_words_clean:
        st = clean_and_stem(w)
        if st and st not in doc_stems_map:
            doc_stems_map[st] = w

    # Raccogliamo le parole del documento che hanno la stessa radice delle parole della query
    comuni_parole_doc = []
    for q_stem, q_word in query_stems_map.items():
        for d_stem, d_word in doc_stems_map.items():
            if q_stem == d_stem or ((q_stem in d_stem or d_stem in q_stem) and min(len(q_stem), len(d_stem)) >= 4):
                if d_word.lower() not in [p.lower() for p in comuni_parole_doc]:
                    comuni_parole_doc.append(d_word)

    uffici = _ottieni_lista(doc.uffici)
    firmatari = _ottieni_lista(doc.firmatari)
    query_words = [t.text.lower().strip() for t in parsed_query if len(t.text.strip()) > 2]

    # Uffici pertinenti: quelli il cui nome contiene una parola della query
    uffici_rilevati = [u for u in uffici if any(w in u.lower() for w in query_words if w not in {"ufficio", "settore", "servizio"})]
    firmatari_rilevati = [f for f in firmatari if any(w in f.lower() for w in query_words if w not in {"ing", "dott", "dott.ssa", "arch", "sindaco", "segretario"})]
    frazioni = _ottieni_lista(doc.frazioni)
    frazioni_rilevate = [f for f in frazioni if any(w in f.lower() for w in query_words if len(w) > 2)]

    tipo_lower = doc.tipologia.lower().strip()
    tipologia_rilevata = any(w in query_words for w in [tipo_lower, tipo_lower.replace("zione", ""), tipo_lower.replace("era", "")])

    punti_condivisi = []

    if tipologia_rilevata:
        punti_condivisi.append(f"alla tipologia di atto cercato ('{doc.tipologia}')")
    if comuni_parole_doc:
        parole = [f"'{p}'" for p in comuni_parole_doc[:3]]
        punti_condivisi.append(
            f"al concetto chiave di {parole[0]}" if len(parole) == 1
            else f"ai concetti chiave di {', '.join(parole[:-1])} e {parole[-1]}"
        )
    if uffici_rilevati:
        uff = [f"'{u}'" for u in uffici_rilevati[:2]]
        punti_condivisi.append(
            f"alla competenza dell'ufficio {uff[0]}" if len(uff) == 1
            else f"alla competenza degli uffici {', '.join(uff[:-1])} e {uff[-1]}"
        )
    if firmatari_rilevati:
        firm = [f"'{f}'" for f in firmatari_rilevati[:2]]
        punti_condivisi.append(
            f"alla firma o supervisione di {firm[0]}" if len(firm) == 1
            else f"alla firma dei funzionari {', '.join(firm[:-1])} e {firm[-1]}"
        )
    if frazioni_rilevate:
        fraz = [f"'{f}'" for f in frazioni_rilevate[:2]]
        punti_condivisi.append(
            f"alla localizzazione geografica presso la frazione o zona {fraz[0]}" if len(fraz) == 1
            else f"alla localizzazione geografica presso le frazioni {', '.join(fraz[:-1])} e {fraz[-1]}"
        )

    percentuale = max(min(int(round(score * 100)), 99), 0)

    if punti_condivisi:
        return f"L'atto corrisponde alla ricerca ({percentuale}%) grazie a riscontri diretti relativi {_formatta_punti(punti_condivisi)}."

    # Fallback semantico puro: usiamo gli embedding delle singole parole per trovare affinità
    emb_query = embedding_model.encode(query_testo)
    lemmi_doc_affini = sorted(
        [(forma, calcola_similarita_coseno(emb_query, embedding_model.encode(forma))) for _lemma, forma in lemmi_doc.items()],
        key=lambda x: x[1], reverse=True
    )
    sost_doc = [f"'{forma}'" for forma, _s in lemmi_doc_affini[:2]]
    sost_query = _ottieni_principali_sostantivi(lemmi_query)

    ricerca_tema = f"incentrata su {', '.join(sost_query)}" if sost_query else f"'{query_testo}'"
    doc_tema = f"tratta tematiche di {', '.join(sost_doc)}" if sost_doc else "tratta argomenti correlati"

    return f"Trovato per affinità concettuale indiretta ({percentuale}%). La ricerca, {ricerca_tema}, si collega semanticamente all'atto che {doc_tema}, operando nello stesso contesto operativo dell'ente."

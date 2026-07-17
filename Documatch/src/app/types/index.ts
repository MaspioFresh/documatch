// ─── Tipi principali dell'applicazione ───────────────────────────────────────

/** Categorie documentali supportate dal sistema. */
export type Tipologia = string;

/** Scheda documentale archiviata nel sistema. */
export interface Doc {
  id: string;
  nome: string;
  descrizione: string | null;
  tipologia: string;
  data: string;          // ISO date (YYYY-MM-DD)
  data_scadenza: string | null;      // ISO date
  uffici: string[];
  firmatari: string[];
  frazioni: string[];
  url_immagine: string | null;
  testo_estratto: string | null;
  stato_elaborazione?: string;
}

export interface RisultatoRicerca {
  documento: Doc;
  punteggio_similarita: number;
  spiegazione_ia: string;
}

export interface User {
  username: string;
  is_admin: boolean;
}

/** Viste dell'applicazione (routing client-side basato su stato). */
export type View = "home" | "detail" | "admin" | "reset";

/** Singolo messaggio nella conversazione col chatbot. */
export interface ChatMessage {
  role: "user" | "bot";
  text: string;
}

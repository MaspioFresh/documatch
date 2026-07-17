/**
 * Dati mock dell'applicazione.
 * In un'implementazione reale questi verrebbero da chiamate API (es. Azure Blob
 * Storage + Cosmos DB). Tutti i dati sono verosimili e localizzati in italiano.
 *
 * OCR_SAMPLES: campioni pre-confezionati per simulare l'output di un OCR.
 * I numeri di protocollo sono generati casualmente al caricamento del modulo,
 * così ogni sessione ha valori diversi — più realistico per la demo.
 */
import type { Doc, Tipologia } from "../types";

export const IMGS = [
  "https://images.unsplash.com/photo-1583521214690-73421a1829a9?w=600&h=400&fit=crop&auto=format",
  "https://images.unsplash.com/photo-1468779036391-52341f60b55d?w=600&h=400&fit=crop&auto=format",
  "https://images.unsplash.com/photo-1516409590654-e8d51fc2d25c?w=600&h=400&fit=crop&auto=format",
  "https://images.unsplash.com/photo-1526656001029-20a71b17f7ba?w=600&h=400&fit=crop&auto=format",
  "https://images.unsplash.com/photo-1562654501-a0ccc0fc3fb1?w=600&h=400&fit=crop&auto=format",
];

export const MOCK: Doc[] = [
  { id: "1", numero: "DEL-042/2025", nome: "Approvazione Piano Triennale delle Opere Pubbliche 2025-2027", descrizione: "Delibera di Giunta Comunale per l'approvazione del Piano Triennale delle Opere Pubbliche relativo al triennio 2025-2027, comprendente interventi di riqualificazione stradale e manutenzione edifici scolastici.", tipologia: "Delibera", data: "2025-03-15", anno: 2025, scadenza: "2027-12-31", uffici: ["Ufficio Tecnico", "Ragioneria"], firme: ["Sindaco Mario Gentile", "Resp. UTC Ing. Rossi"], immagine: IMGS[0], tags: ["opere pubbliche", "pianificazione", "bilancio"], frazioni: [], testoOcr: "" },
  { id: "2", numero: "AUT-017/2025", nome: "Autorizzazione Paesaggistica – Via Roma 14", descrizione: "Autorizzazione paesaggistica per il recupero e restauro conservativo della facciata esterna dell'immobile sito in Via Roma 14, nel rispetto dei vincoli paesaggistici ai sensi del D.Lgs. 42/2004.", tipologia: "Autorizzazione", data: "2025-01-22", anno: 2025, scadenza: "2025-12-31", uffici: ["Ufficio Edilizia Privata"], firme: ["Resp. Edilizia Arch. Ferrara"], immagine: IMGS[1], tags: ["paesaggio", "restauro", "edilizia"], frazioni: [], testoOcr: "" },
  { id: "3", numero: "PUC-001/2024", nome: "Piano Urbanistico Comunale – Variante n. 3", descrizione: "Adozione della variante n. 3 al Piano Urbanistico Comunale (PUC) vigente, con modifiche alle zone omogenee B2 e D1 nel rispetto delle norme regionali di governo del territorio.", tipologia: "Piano Comunale", data: "2024-11-08", anno: 2024, scadenza: "", uffici: ["Ufficio Tecnico", "Pianificazione Urbanistica"], firme: ["Sindaco Mario Gentile", "Ing. Rossi", "Arch. Ferrara"], immagine: IMGS[2], tags: ["urbanistica", "variante", "PUC"], frazioni: [], testoOcr: "" },
  { id: "4", numero: "DEC-008/2025", nome: "Decreto Sindacale – Nomina Assessori", descrizione: "Decreto del Sindaco per la nomina dei componenti della Giunta Comunale, con attribuzione delle deleghe assessoriali per il mandato amministrativo 2025-2030.", tipologia: "Decreto", data: "2025-06-01", anno: 2025, scadenza: "2030-05-31", uffici: ["Segreteria Comunale"], firme: ["Sindaco Mario Gentile"], immagine: IMGS[3], tags: ["giunta", "nomine", "mandato"], frazioni: [], testoOcr: "" },
  { id: "5", numero: "ORD-023/2025", nome: "Ordinanza Chiusura Traffico Piazza Municipio", descrizione: "Ordinanza del Sindaco per la temporanea chiusura al traffico veicolare di Piazza del Municipio in occasione delle manifestazioni estive dal 15 luglio al 31 agosto 2025.", tipologia: "Ordinanza", data: "2025-07-01", anno: 2025, scadenza: "2025-08-31", uffici: ["Polizia Municipale", "Ufficio Tecnico"], firme: ["Sindaco Mario Gentile", "Comandante PM Resp. Greco"], immagine: IMGS[4], tags: ["traffico", "viabilita", "manifestazioni"], frazioni: [], testoOcr: "" },
  { id: "6", numero: "DET-055/2024", nome: "Determina Affidamento Servizio Manutenzione Verde Pubblico", descrizione: "Determinazione del Responsabile del Settore Lavori Pubblici per l'affidamento diretto del servizio di manutenzione ordinaria del verde pubblico comunale per l'anno 2024.", tipologia: "Determina", data: "2024-04-12", anno: 2024, scadenza: "2024-12-31", uffici: ["Settore Lavori Pubblici"], firme: ["Resp. LL.PP. Geom. Marino"], immagine: IMGS[0], tags: ["verde pubblico", "appalti", "manutenzione"], frazioni: [], testoOcr: "" },
  { id: "7", numero: "DEL-031/2024", nome: "Approvazione Bilancio Preventivo 2024", descrizione: "Delibera del Consiglio Comunale per l'approvazione del bilancio di previsione finanziario dell'esercizio 2024-2026, comprensivo del Documento Unico di Programmazione (DUP).", tipologia: "Delibera", data: "2024-12-28", anno: 2024, scadenza: "2026-12-31", uffici: ["Ragioneria", "Segreteria Comunale"], firme: ["Sindaco Mario Gentile", "Ragioniere Capo Dott. Aiello"], immagine: IMGS[1], tags: ["bilancio", "programmazione", "DUP"], frazioni: [], testoOcr: "" },
  { id: "8", numero: "AUT-009/2024", nome: "Autorizzazione Commerciale – Mercato Ambulante", descrizione: "Rilascio autorizzazione per lo svolgimento del mercato ambulante settimanale in Piazza della Repubblica ogni giovedì, con assegnazione dei posteggi secondo il piano approvato.", tipologia: "Autorizzazione", data: "2024-02-05", anno: 2024, scadenza: "2024-12-31", uffici: ["SUAP", "Polizia Municipale"], firme: ["Resp. SUAP Dott.ssa Conti"], immagine: IMGS[2], tags: ["commercio", "mercato", "SUAP"], frazioni: [], testoOcr: "" },
  { id: "9", numero: "DET-078/2025", nome: "Determina Acquisto Attrezzature Informatiche", descrizione: "Determinazione per l'acquisto di n. 10 personal computer e relativi accessori per il rinnovo del parco informatico degli uffici comunali, tramite convenzione Consip.", tipologia: "Determina", data: "2025-02-18", anno: 2025, scadenza: "", uffici: ["Ufficio CED", "Ragioneria"], firme: ["Resp. CED P.I. Caruso"], immagine: IMGS[3], tags: ["informatica", "Consip", "acquisti"], frazioni: [], testoOcr: "" },
  { id: "10", numero: "ORD-011/2024", nome: "Ordinanza Antincendio Boschi – Estate 2024", descrizione: "Ordinanza sindacale per la prevenzione degli incendi boschivi nel periodo estivo ad alto rischio, con prescrizioni per l'accesso alle aree boscate comunali.", tipologia: "Ordinanza", data: "2024-06-20", anno: 2024, scadenza: "2024-09-30", uffici: ["Protezione Civile", "Polizia Municipale"], firme: ["Sindaco Mario Gentile"], immagine: IMGS[4], tags: ["antincendio", "boschi", "protezione civile"], frazioni: [], testoOcr: "" },
  { id: "11", numero: "PUC-002/2025", nome: "Piano di Recupero Centro Storico", descrizione: "Approvazione del Piano di Recupero del Centro Storico di Montalto Uffugo con interventi di riqualificazione urbana, restauro edilizio e valorizzazione del patrimonio architettonico.", tipologia: "Piano Comunale", data: "2025-04-30", anno: 2025, scadenza: "", uffici: ["Ufficio Tecnico", "Pianificazione Urbanistica", "Cultura"], firme: ["Sindaco Mario Gentile", "Assessore Cultura Dott.ssa Bianchi", "Arch. Ferrara"], immagine: IMGS[0], tags: ["centro storico", "riqualificazione", "patrimonio"], frazioni: [], testoOcr: "" },
  { id: "12", numero: "DEC-003/2024", nome: "Decreto Nomina Responsabili di Settore", descrizione: "Decreto del Sindaco per la nomina dei responsabili dei settori comunali in attuazione dell'art. 50 del D.Lgs. 267/2000 (TUEL) per il biennio 2024-2025.", tipologia: "Decreto", data: "2024-01-10", anno: 2024, scadenza: "2025-12-31", uffici: ["Segreteria Comunale"], firme: ["Sindaco Mario Gentile", "Segretario Comunale Dott. Mancini"], immagine: IMGS[1], tags: ["nomine", "organizzazione", "TUEL"], frazioni: [], testoOcr: "" },
];

export const BADGE_PALETTE = [
  "bg-blue-100 text-blue-800",
  "bg-emerald-100 text-emerald-800",
  "bg-purple-100 text-purple-800",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-800",
  "bg-teal-100 text-teal-800",
  "bg-orange-100 text-orange-800",
  "bg-indigo-100 text-indigo-800",
  "bg-cyan-100 text-cyan-800",
  "bg-pink-100 text-pink-800",
  "bg-fuchsia-100 text-fuchsia-800",
  "bg-violet-100 text-violet-800",
  "bg-sky-100 text-sky-800",
  "bg-lime-100 text-lime-800",
  "bg-yellow-100 text-yellow-800",
  "bg-red-100 text-red-800",
  "bg-green-100 text-green-800",
  "bg-blue-50 text-blue-700",
  "bg-indigo-50 text-indigo-700",
  "bg-rose-50 text-rose-700",
  "bg-amber-50 text-amber-700",
];

export const TIPI: Tipologia[] = ["Delibera", "Autorizzazione", "Piano Comunale", "Decreto", "Ordinanza", "Determina"];

export const ANNI = Array.from(new Set(MOCK.map((d) => d.anno))).sort((a, b) => b - a);

export const DEFAULT_UFFICI = [
  "Ufficio Tecnico", "Ragioneria", "Segreteria Comunale", "Pianificazione Urbanistica",
  "Ufficio Edilizia Privata", "Settore Lavori Pubblici", "Polizia Municipale",
  "SUAP", "Protezione Civile", "Ufficio CED", "Cultura",
];

export const DEFAULT_FRAZIONI = [
  "Montalto Uffugo Scalo", "Settimo", "Taverna", "Serra Vetrana",
  "Piane Crati", "Andreotta", "Atti", "Borgo Partenope", "Fiego",
];

export const DEFAULT_FIRMATARI = [
  "Sindaco Mario Gentile", "Segretario Comunale Dott. Mancini", "Resp. UTC Ing. Rossi",
  "Arch. Ferrara", "Geom. Marino", "Ragioniere Capo Dott. Aiello",
  "Resp. SUAP Dott.ssa Conti", "Comandante PM Resp. Greco", "Resp. CED P.I. Caruso",
  "Assessore Cultura Dott.ssa Bianchi",
];

export const EMPTY_FORM: Omit<Doc, "id"> = {
  nome: "", descrizione: "", tipologia: "Delibera",
  data: new Date().toISOString().slice(0, 10),
  data_scadenza: null, uffici: [], firmatari: [], frazioni: [], url_immagine: "", testo_estratto: null,
};

export const OCR_SAMPLES: Array<{ nome: string; descrizione: string; tipologia: Tipologia }> = [
  {
    nome: "Delibera di Giunta – Approvazione Progetto Esecutivo",
    descrizione: "Testo estratto tramite OCR: approvazione del progetto esecutivo relativo ai lavori di manutenzione straordinaria della viabilità comunale.",
    tipologia: "Delibera",
  },
  {
    nome: "Ordinanza Sindacale – Misure di Sicurezza",
    descrizione: "Testo estratto tramite OCR: ordinanza per l'adozione di misure di sicurezza urgenti in seguito a sopralluogo tecnico.",
    tipologia: "Ordinanza",
  },
  {
    nome: "Determina Dirigenziale – Affidamento Incarico",
    descrizione: "Testo estratto tramite OCR: determinazione per l'affidamento diretto di incarico professionale per attività di supporto tecnico.",
    tipologia: "Determina",
  },
];

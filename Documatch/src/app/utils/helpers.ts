import { BADGE_PALETTE } from "../data/mockData";

/** Formatta una data ISO in formato leggibile italiano (es. "15 mar 2025"). */
export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

/** Restituisce true se la scadenza è nel passato. Stringa vuota = mai scaduto. */
export function isExpired(scadenza: string): boolean {
  return !!scadenza && new Date(scadenza) < new Date();
}

/** Genera un ID casuale breve per le nuove schede (non richiede UUID completo). */
export function newId(): string {
  return Math.random().toString(36).slice(2, 9);
}

/**
 * Assegna un colore badge deterministico basato sul nome della tipologia.
 * La somma dei char code garantisce che lo stesso nome produca sempre lo stesso colore,
 * senza bisogno di una mappa esplicita Tipologia→colore.
 */
export function badgeColor(name: string): string {
  const sum = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return BADGE_PALETTE[sum % BADGE_PALETTE.length];
}

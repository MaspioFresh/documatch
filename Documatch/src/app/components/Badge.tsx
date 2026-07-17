import type { Tipologia } from "../types";
import { badgeColor } from "../utils/helpers";

interface BadgeProps {
  tipo: Tipologia;
}

/**
 * Pill colorata che identifica la tipologia di un documento.
 * Il colore è deterministico sul nome (vedi badgeColor), quindi coerente
 * in tutta l'app senza bisogno di passarlo come prop.
 */
export function Badge({ tipo }: BadgeProps) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium font-mono ${badgeColor(tipo)}`}>
      {tipo}
    </span>
  );
}

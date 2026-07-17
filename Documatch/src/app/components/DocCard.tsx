import type { Doc } from "../types";
import { fmtDate, isExpired } from "../utils/helpers";
import { getImageUrl } from "../services/api";
import { Badge } from "./Badge";

import { Pencil, Trash2 } from "lucide-react";

interface DocCardProps {
  doc: Doc;
  spiegazione_ia?: string;
  punteggio_similarita?: number;
  onClick: () => void;
  adminUnlocked?: boolean;
  onEdit?: (doc: Doc) => void;
  onDelete?: (id: string) => void;
  selected?: boolean;
  onSelectToggle?: (id: string) => void;
}

/**
 * Riga documento nella visualizzazione a lista.
 */
export function DocCard({ doc, spiegazione_ia, punteggio_similarita, onClick, adminUnlocked, onEdit, onDelete, selected, onSelectToggle }: DocCardProps) {
  const expired = isExpired(doc.data_scadenza);

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick(); }}
      className={`group/card h-full relative bg-card border rounded-lg overflow-hidden text-left hover:shadow-md transition-all duration-200 flex flex-col cursor-pointer ${selected ? "border-primary ring-1 ring-primary" : "border-border hover:border-primary/30"}`}
    >
      <div className="flex flex-row w-full flex-1">
        {/* Immagine in proporzione A4 portrait — funge da trigger peer per il preview */}
        <div className="peer/img relative shrink-0 w-[100px] bg-muted overflow-hidden" style={{ aspectRatio: "210/297" }}>
          <img
            src={getImageUrl(doc.url_immagine)}
            alt={doc.nome}
            className="w-full h-full object-cover"
          />
          {expired && (
            <span className="absolute top-1.5 left-1.5 bg-red-600 text-white text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded leading-none">
              Scaduto
            </span>
          )}
          {punteggio_similarita !== undefined && (
            <div className="absolute bottom-0 left-0 right-0 bg-primary/90 backdrop-blur-sm text-primary-foreground text-center py-1 text-[9px] font-bold uppercase tracking-wider">
              Affinità: {Math.round(punteggio_similarita * 100)}%
            </div>
          )}
        </div>

        {/* Anteprima centrata a schermo */}
        <div
          className="opacity-0 peer-hover/img:opacity-100 transition-opacity duration-150 fixed -z-10 peer-hover/img:z-[9999] w-[420px] shadow-2xl rounded-xl overflow-hidden border border-border ring-4 ring-black/10"
          style={{ aspectRatio: "210/297", left: "50%", top: "50%", transform: "translate(-50%, -50%)", pointerEvents: "none" }}
        >
          <img src={getImageUrl(doc.url_immagine)} alt={doc.nome} className="w-full h-full object-cover" style={{ pointerEvents: "none" }} />
        </div>

        {/* Metadati testuali */}
        <div className="p-4 flex flex-col gap-1.5 flex-1 min-w-0">
          <div className="flex items-center justify-end gap-1 shrink-0 mb-1">
            {adminUnlocked && (
              <>
                <div onClick={(e) => { e.stopPropagation(); onEdit?.(doc); }} className="p-1.5 bg-background border border-border text-muted-foreground hover:text-primary hover:border-primary rounded-md shadow-sm transition-colors cursor-pointer" title="Modifica">
                  <Pencil className="w-3.5 h-3.5" />
                </div>
                <div onClick={(e) => { e.stopPropagation(); onDelete?.(doc.id); }} className="p-1.5 bg-background border border-border text-muted-foreground hover:text-accent hover:border-accent rounded-md shadow-sm transition-colors cursor-pointer" title="Elimina">
                  <Trash2 className="w-3.5 h-3.5" />
                </div>
              </>
            )}
            {onSelectToggle && (
              <div
                onClick={(e) => { e.stopPropagation(); onSelectToggle(doc.id); }}
                className={`p-1.5 bg-background border rounded-md shadow-sm transition-colors cursor-pointer flex items-center justify-center ${selected ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`}
                title="Seleziona"
              >
                <input
                  type="checkbox"
                  checked={selected || false}
                  readOnly
                  className="w-3.5 h-3.5 rounded-sm border-gray-300 text-primary focus:ring-primary cursor-pointer pointer-events-none"
                />
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge tipo={doc.tipologia} />
            {doc.stato_elaborazione === 'in_elaborazione' && (
              <span className="bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded flex items-center gap-1 break-words">
                <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse shrink-0"></span>
                In elaborazione OCR...
              </span>
            )}
            {doc.stato_elaborazione === 'errore' && (
              <span className="bg-red-100 text-red-800 border border-red-300 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded break-words">
                ⚠️ Errore OCR
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold leading-snug line-clamp-2">{doc.nome}</h3>
          <p className="text-xs text-muted-foreground line-clamp-2 flex-1">{doc.descrizione}</p>
          <div className={`pt-2 border-t flex flex-col gap-1 text-xs text-muted-foreground mt-auto ${expired ? "border-t-2 border-red-500" : "border-t-2 border-primary"}`}>
            <div className="font-mono text-right shrink-0 pb-1 border-b border-border/40">
              {fmtDate(doc.data)}
              {doc.data_scadenza && (
                <>
                  <span className="mx-1.5">·</span>
                  <span className={expired ? "text-red-500 font-bold" : ""}>{fmtDate(doc.data_scadenza)}</span>
                </>
              )}
            </div>
            <span className="break-words">Uffici: {doc.uffici.join(" · ")}</span>
            {doc.firmatari && doc.firmatari.length > 0 && (
              <span className="italic break-words">Firme: {doc.firmatari.join(" · ")}</span>
            )}
          </div>
        </div>
      </div>

      {/* Spiegazione IA (Mostrata solo se proviene dalla ricerca semantica o correlati e c'è del testo utile) */}
      {(spiegazione_ia && spiegazione_ia !== "Trovato per similarità semantica." && spiegazione_ia !== "Trovato per similarità con il testo estratto dalla foto.") && (
        <div className="bg-primary/5 border-t border-primary/10 p-3 flex gap-2 w-full text-xs text-primary/80 shrink-0 h-[240px] overflow-y-auto">
          <svg className="w-4 h-4 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span className="leading-relaxed">{spiegazione_ia}</span>
        </div>
      )}
    </div>
  );
}

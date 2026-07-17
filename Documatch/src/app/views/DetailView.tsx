import { useState, useEffect } from "react";
import { ChevronLeft, Pencil, Trash2 } from "lucide-react";
import type { Doc } from "../types";
import { fmtDate, isExpired } from "../utils/helpers";
import { Badge } from "../components/Badge";
import { DocCard } from "../components/DocCard";
import { ChatModal } from "../components/ChatModal";
import { documentiService } from "../services/documentiService";

/**
 * Vista dettaglio di un singolo documento.
 * Gestisce localmente solo `chatOpen` — è l'unico stato che non ha senso
 * sollevare ad App, perché il modal esiste solo in questa view.
 * I "documenti correlati" mostrano fino a 3 schede con stessa tipologia o
 * stesso anno, escludendo il documento corrente.
 */
interface DetailViewProps {
  doc: Doc;
  allDocs: Doc[];
  onBack: () => void;
  onSelectDoc: (id: string) => void;
  adminUnlocked?: boolean;
  onEdit?: (doc: Doc) => void;
  onDelete?: (id: string) => void;
}

export function DetailView({ doc, allDocs, onBack, onSelectDoc, adminUnlocked, onEdit, onDelete }: DetailViewProps) {
  const [chatOpen, setChatOpen] = useState(false);
  const [related, setRelated] = useState<any[]>([]);
  const [loadingRelated, setLoadingRelated] = useState(true);

  useEffect(() => {
    async function loadRecommendations() {
      setLoadingRelated(true);
      try {
        const recs = await documentiService.getRecommendations(doc.id);
        // Take up to 3 recommendations
        setRelated(recs.slice(0, 3));
      } catch (err) {
        console.error("Errore raccomandazioni", err);
      } finally {
        setLoadingRelated(false);
      }
    }
    loadRecommendations();
  }, [doc.id]);

  return (
    <main className="w-full min-w-0 max-w-5xl mx-auto px-4 py-8">
      {chatOpen && <ChatModal doc={doc} onClose={() => setChatOpen(false)} />}

      <div className="flex flex-wrap sm:items-center justify-between gap-4 mb-6">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ChevronLeft className="w-4 h-4" /> Torna all&apos;archivio
        </button>
        <div className="flex items-center gap-3">
          {adminUnlocked && (
            <div className="flex items-center gap-1.5 border-r border-border pr-3">
              <button onClick={() => onEdit?.(doc)} className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-background border border-border text-foreground hover:text-primary hover:border-primary rounded-md shadow-sm transition-colors">
                <Pencil className="w-4 h-4" /> Modifica
              </button>
              <button onClick={() => onDelete?.(doc.id)} className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-background border border-border text-foreground hover:text-accent hover:border-accent rounded-md shadow-sm transition-colors">
                <Trash2 className="w-4 h-4" /> Elimina
              </button>
            </div>
          )}
          <button onClick={() => setChatOpen(true)}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            Chiedi al chatbot
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm mb-8">
        <div className="grid md:grid-cols-2">
          <div className="bg-muted">
            <img src={doc.url_immagine || ""} alt={doc.nome} className="w-full object-cover aspect-[210/297]" />
          </div>
          <div className="p-6 flex flex-col gap-4">
            <div className="flex items-start justify-between gap-2">
              <Badge tipo={doc.tipologia} />
            </div>
            <h1 className="text-xl font-bold leading-snug" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>{doc.nome}</h1>
            <p className="text-sm text-muted-foreground leading-relaxed">{doc.descrizione}</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm mt-2">
              <div>
                <dt className="text-xs text-muted-foreground uppercase tracking-wide mb-0.5">Data</dt>
                <dd className="font-mono">{fmtDate(doc.data)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground uppercase tracking-wide mb-0.5">Scadenza</dt>
                <dd className="flex items-center gap-2 font-mono">
                  {doc.data_scadenza ? fmtDate(doc.data_scadenza) : <span className="text-muted-foreground italic text-xs">–</span>}
                  {isExpired(doc.data_scadenza) && <span className="bg-red-100 text-red-700 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded">Scaduto</span>}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Uffici coinvolti</dt>
                <dd className="flex flex-wrap gap-1">
                  {doc.uffici.map((u) => <span key={u} className="bg-secondary text-secondary-foreground text-xs px-2 py-0.5 rounded">{u}</span>)}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted-foreground uppercase tracking-wide mb-0.5">Firme</dt>
                <dd className="text-sm">{doc.firmatari.join(" · ")}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <h2 className="text-base font-semibold mb-4 uppercase tracking-wide" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Documenti correlati</h2>
      {loadingRelated ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium">L&apos;intelligenza artificiale sta analizzando i documenti simili...</p>
        </div>
      ) : related.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {related.map((d) => <DocCard key={d.documento.id} doc={d.documento} spiegazione_ia={d.spiegazione_ia} punteggio_similarita={d.punteggio_similarita} onClick={() => onSelectDoc(d.documento.id)} />)}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic">Nessun documento strettamente correlato trovato.</p>
      )}
    </main>
  );
}

import { useState, useMemo, useRef, useEffect } from "react";
import { Search, ScanSearch, X, FileText, SlidersHorizontal, Download, Trash2 } from "lucide-react";
import type { Doc } from "../types";

import { isExpired } from "../utils/helpers";
import { DocCard } from "../components/DocCard";
import { ricercaService } from "../services/ricercaService";
import { documentiService } from "../services/documentiService";
import { useDialog } from "../contexts/DialogContext";

function MultiSelectFilter({ label, options, selected, logic, onSelect, onLogicChange }: any) {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const toggle = (val: string) => {
    if (selected.includes(val)) onSelect(selected.filter((v: string) => v !== val));
    else onSelect([...selected, val]);
  };
  const filteredOptions = options.filter(([k, v]: [string, string]) => v.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`text-sm border rounded-lg pl-2 pr-7 py-1.5 text-left focus:outline-none focus:ring-2 focus:ring-ring transition-colors flex items-center justify-between min-w-[110px] w-full ${selected.length > 0 ? "bg-primary text-primary-foreground border-primary" : "bg-input-background border-border text-foreground"}`}
      >
        <span className="truncate max-w-[140px]">{selected.length > 0 ? `${label} (${selected.length})` : label}</span>
      </button>
      {selected.length > 0 && (
        <button onClick={() => onSelect([])} className="absolute right-2 top-1/2 -translate-y-1/2 text-primary-foreground/70 hover:text-primary-foreground z-10 p-1"><X className="w-3.5 h-3.5" /></button>
      )}

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 mt-1 w-64 bg-card border border-border rounded-lg shadow-xl z-50 overflow-hidden flex flex-col">
            <div className="p-1.5 px-2 border-b border-border flex items-center justify-between bg-muted/50">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase">Filtro:</span>
              <div className="flex bg-input-background border border-border rounded overflow-hidden">
                <button onClick={() => onLogicChange("or")} className={`px-2 py-1 text-[11px] leading-none ${logic === "or" ? "bg-primary text-primary-foreground font-medium" : "text-muted-foreground hover:bg-muted"}`}>ALMENO UNO</button>
                <button onClick={() => onLogicChange("and")} className={`px-2 py-1 text-[11px] leading-none ${logic === "and" ? "bg-primary text-primary-foreground font-medium" : "text-muted-foreground hover:bg-muted"}`}>TUTTI</button>
              </div>
            </div>
            <div className="p-1.5 border-b border-border bg-card">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                <input 
                  type="text" 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Cerca opzione..." 
                  className="w-full pl-6 pr-2 py-1 text-xs border border-border rounded bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
            <div className="max-h-60 overflow-y-auto overflow-x-hidden p-1">
              {filteredOptions.length === 0 ? (
                <div className="px-2 py-3 text-center text-xs text-muted-foreground">Nessuna opzione trovata</div>
              ) : (
                filteredOptions.map(([k, v]: [string, string]) => (
                  <label key={k} className="flex items-start gap-2 px-2 py-1 hover:bg-muted rounded cursor-pointer text-sm">
                    <input type="checkbox" checked={selected.includes(k)} onChange={() => toggle(k)} className="mt-0.5 rounded border-input text-primary focus:ring-primary h-3.5 w-3.5 shrink-0" />
                    <span className="leading-snug">{v}</span>
                  </label>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Vista principale: barra di ricerca sticky + lista documenti filtrata.
 *
 * Tutta la logica di filtro è locale a questa view (query, filterTipo, ecc.)
 * poiché non serve condividerla altrove. I presets (uffici, firmatari, frazioni)
 * vengono da App per mantenere coerenza con AdminView: se un admin aggiunge un
 * ufficio, compare subito anche qui nel dropdown.
 *
 * La ricerca per immagine (OCR) è simulata: estrae il nome del file come query
 * testuale dopo un ritardo di 1.5s, riproducendo il feedback UX di un OCR reale.
 * I documenti scaduti vengono portati in fondo dall'ordinamento nel useMemo.
 */
interface HomeViewProps {
  docs: Doc[];
  ufficiPreset: string[];
  firmatariPreset: string[];
  frazioniPreset: string[];
  tipiPreset: string[];
  onSelectDoc: (id: string) => void;
  adminUnlocked?: boolean;
  onEdit?: (doc: Doc) => void;
  onDelete?: (id: string) => void;
  onRefresh?: () => void;
}

export function HomeView({ docs, ufficiPreset, firmatariPreset, frazioniPreset, tipiPreset, onSelectDoc, adminUnlocked, onEdit, onDelete, onRefresh }: HomeViewProps) {
  const { showAlert, showConfirm } = useDialog();
  const [query, setQuery] = useState("");
  const [filterTipo, setFilterTipo] = useState<string[]>([]);
  const [filterTipoLogic, setFilterTipoLogic] = useState<"and" | "or">("or");
  const [filterAnno, setFilterAnno] = useState<string[]>([]);
  const [filterAnnoLogic, setFilterAnnoLogic] = useState<"and" | "or">("or");
  const [filterUfficio, setFilterUfficio] = useState<string[]>([]);
  const [filterUfficioLogic, setFilterUfficioLogic] = useState<"and" | "or">("or");
  const [filterFirmatario, setFilterFirmatario] = useState<string[]>([]);
  const [filterFirmatarioLogic, setFilterFirmatarioLogic] = useState<"and" | "or">("or");
  const [filterFrazione, setFilterFrazione] = useState<string[]>([]);
  const [filterFrazioneLogic, setFilterFrazioneLogic] = useState<"and" | "or">("or");
  const [imageMode, setImageMode] = useState(false);
  const [imgPreview, setImgPreview] = useState<string | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const ocrInputRef = useRef<HTMLInputElement>(null);
  const [semanticResults, setSemanticResults] = useState<any[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());

  const handleSelectToggle = (id: string) => {
    const newSet = new Set(selectedDocs);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedDocs(newSet);
  };

  const handleBulkExport = async () => {
    if (selectedDocs.size === 0) return;
    const formatChoice = await showConfirm(
      "Formato Esportazione", 
      `Scegli in quale formato esportare i metadati dei ${selectedDocs.size} documenti all'interno dello ZIP.`,
      "JSON",
      "CSV"
    );
    if (formatChoice === null) return;
    
    const format = formatChoice ? "json" : "csv";

    try {
      await documentiService.exportBulk(Array.from(selectedDocs), format);
      await showAlert("Esportazione Completata", "L'archivio ZIP è stato scaricato con successo.");
    } catch (err: any) {
      await showAlert("Errore", "Errore esportazione: " + err.message);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocs.size === 0) return;
    const confirmed = await showConfirm("Conferma Eliminazione Massiva", `Sei assolutamente sicuro di voler eliminare DEFINITIVAMENTE ${selectedDocs.size} documenti? L'operazione NON è reversibile.`);
    if (!confirmed) return;
    
    try {
      const res = await documentiService.bulkDelete(Array.from(selectedDocs));
      await showAlert("Eliminazione Completata", res.messaggio);
      setSelectedDocs(new Set());
      if (onRefresh) onRefresh();
    } catch (err: any) {
      await showAlert("Errore", "Errore eliminazione: " + err.message);
    }
  };

  const allUffici = useMemo(
    () => Array.from(new Set([...ufficiPreset, ...docs.flatMap((d) => d.uffici)])).sort(),
    [ufficiPreset, docs]
  );

  const allAnni = useMemo(
    () => Array.from(new Set(docs.map((d) => d.data.slice(0, 4)))).sort((a, b) => Number(b) - Number(a)),
    [docs]
  );

  useEffect(() => {
    if (!query.trim()) {
      setSemanticResults(null);
      return;
    }
    const t = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await ricercaService.ricercaTestuale(query, {
          tipologia: filterTipo.length ? filterTipo : undefined,
          tipologia_logic: filterTipoLogic,
          ufficio: filterUfficio.length ? filterUfficio : undefined,
          ufficio_logic: filterUfficioLogic,
          firmatario: filterFirmatario.length ? filterFirmatario : undefined,
          firmatario_logic: filterFirmatarioLogic,
          frazione: filterFrazione.length ? filterFrazione : undefined,
          frazione_logic: filterFrazioneLogic,
        });
        setSemanticResults(res);
      } catch (err) {
        console.error("Errore ricerca testuale", err);
      } finally {
        setIsSearching(false);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [query, filterTipo, filterAnno, filterUfficio, filterFirmatario, filterFrazione]);

  const filtered = useMemo(() => {
    if (semanticResults) return semanticResults;

    return docs.filter((d) => {
      const q = query.toLowerCase();

      const matchTipologia = filterTipo.length === 0 ||
        (filterTipoLogic === "and" ? filterTipo.every(t => d.tipologia === t) : filterTipo.some(t => d.tipologia === t));

      const matchAnno = filterAnno.length === 0 ||
        (filterAnnoLogic === "and" ? filterAnno.every(a => d.data.startsWith(a)) : filterAnno.some(a => d.data.startsWith(a)));

      const matchUfficio = filterUfficio.length === 0 ||
        (filterUfficioLogic === "and" ? filterUfficio.every(u => d.uffici.includes(u)) : filterUfficio.some(u => d.uffici.includes(u)));

      const matchFirmatario = filterFirmatario.length === 0 ||
        (filterFirmatarioLogic === "and" ? filterFirmatario.every(f => d.firmatari.includes(f)) : filterFirmatario.some(f => d.firmatari.includes(f)));

      const hasTuttoIlComune = (d.frazioni || []).some(f => f.toLowerCase() === "tutto il comune");
      const matchFrazione = filterFrazione.length === 0 || hasTuttoIlComune ||
        (filterFrazioneLogic === "and" ? filterFrazione.every(f => (d.frazioni || []).includes(f)) : filterFrazione.some(f => (d.frazioni || []).includes(f)));

      return (
        (!q || d.nome.toLowerCase().includes(q) || (d.descrizione && d.descrizione.toLowerCase().includes(q)) || (d.testo_estratto ?? "").toLowerCase().includes(q)) &&
        matchTipologia && matchAnno && matchUfficio && matchFirmatario && matchFrazione
      );
    }).sort((a, b) => Number(isExpired(a.data_scadenza)) - Number(isExpired(b.data_scadenza)));
  }, [docs, query, filterTipo, filterTipoLogic, filterAnno, filterAnnoLogic, filterUfficio, filterUfficioLogic, filterFirmatario, filterFirmatarioLogic, filterFrazione, filterFrazioneLogic, semanticResults]);

  async function handleImageDrop(file: File) {
    setImgPreview(URL.createObjectURL(file));
    setOcrLoading(true);
    try {
      const res = await ricercaService.ricercaImmagine(file);
      setQuery(res.testo_estratto_ocr);
    } catch (err) {
      await showAlert("Errore", "Errore durante l'analisi OCR");
    } finally {
      setOcrLoading(false);
    }
  }

  function resetFilters() {
    setQuery(""); setFilterTipo([]); setFilterAnno([]); setFilterUfficio([]);
    setFilterFirmatario([]); setFilterFrazione([]); setImgPreview(null);
  }

  const hasActiveFilters = query || filterTipo.length > 0 || filterAnno.length > 0 || filterUfficio.length > 0 || filterFirmatario.length > 0 || filterFrazione.length > 0;

  return (
    <main className="w-full min-w-0 max-w-[1400px] mx-auto px-4 py-8">
      <div className="sticky top-[57px] z-40 bg-background pb-4 -mx-4 px-4 pt-1">
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          {/* Tabs modalità */}
          <div className="flex flex-col sm:flex-row gap-1 bg-muted rounded-lg p-1 w-full sm:w-fit mb-4">
            <button onClick={() => { setImageMode(false); setImgPreview(null); setQuery(""); }}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${!imageMode ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              <Search className="w-3.5 h-3.5" /> Ricerca testuale
            </button>
            <button onClick={() => { setImageMode(true); setFilterTipo([]); setFilterAnno([]); setFilterUfficio([]); setFilterFirmatario([]); setFilterFrazione([]); }}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${imageMode ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              <ScanSearch className="w-3.5 h-3.5" /> Ricerca per immagine (OCR)
            </button>
          </div>

          {/* Ricerca testuale */}
          {!imageMode && (
            <div className="flex gap-2 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Cerca per nome, parole chiave…"
                  className="w-full pl-9 pr-10 py-2.5 bg-input-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                {isSearching && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                  </div>
                )}
              </div>
              <button 
                onClick={() => setShowFilters(!showFilters)} 
                className={`flex items-center justify-center gap-2 px-3 py-2.5 border rounded-lg transition-colors ${showFilters || hasActiveFilters ? 'bg-primary text-primary-foreground border-primary' : 'bg-input-background text-foreground border-border hover:bg-muted'}`}
                title="Mostra/nascondi filtri avanzati"
              >
                <SlidersHorizontal className="w-4 h-4" />
                <span className="hidden sm:inline text-sm font-medium">Filtri</span>
              </button>
            </div>
          )}

          {/* OCR upload */}
          {imageMode && (
            <div className="mb-4">
              {!imgPreview ? (
                <div className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-primary/30 rounded-xl p-8 cursor-pointer hover:bg-secondary/40 transition-colors group"
                  onClick={(e) => { e.stopPropagation(); e.preventDefault(); ocrInputRef.current?.click(); }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleImageDrop(f); }}>
                  <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                    <ScanSearch className="w-6 h-6 text-primary/60" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-foreground">Carica la prima pagina del documento</p>
                    <p className="text-xs text-muted-foreground mt-1">Trascina qui oppure <span className="text-primary font-medium">clicca per selezionare</span> — JPG, PNG, PDF</p>
                  </div>
                  <p className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">Il testo verrà estratto automaticamente tramite OCR</p>
                  <input ref={ocrInputRef} type="file" accept="image/*,.pdf" className="hidden" onClick={(e) => e.stopPropagation()} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImageDrop(f); }} />
                </div>
              ) : (
                <div className="flex items-center gap-4 bg-secondary/40 border border-border rounded-xl p-4">
                  <img src={imgPreview} alt="preview" className="w-16 h-16 object-cover rounded-lg border border-border flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    {ocrLoading
                      ? <div className="flex items-center gap-2 text-sm text-foreground font-medium"><span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin inline-block flex-shrink-0" />Analisi OCR in corso…</div>
                      : <><p className="text-sm font-medium text-foreground">Analisi OCR completata</p><p className="text-xs text-muted-foreground mt-0.5">Testo estratto: <span className="font-mono text-foreground">&ldquo;{query}&rdquo;</span></p></>
                    }
                  </div>
                  <button onClick={() => { setImgPreview(null); setQuery(""); }} className="p-1.5 text-muted-foreground hover:text-accent transition-colors flex-shrink-0"><X className="w-4 h-4" /></button>
                </div>
              )}
            </div>
          )}

          {/* Filtri — nascosti in modalità OCR o se chiusi */}
          {!imageMode && showFilters && (
            <div className="grid grid-cols-2 md:flex md:flex-wrap items-start md:items-center gap-2 sm:gap-1.5 mb-2">
              {([
                ["Tipologia", filterTipo, setFilterTipo, filterTipoLogic, setFilterTipoLogic, tipiPreset.map((t) => [t, t])],
                ["Anno", filterAnno, setFilterAnno, filterAnnoLogic, setFilterAnnoLogic, allAnni.map((a) => [String(a), String(a)])],
                ["Ufficio", filterUfficio, setFilterUfficio, filterUfficioLogic, setFilterUfficioLogic, allUffici.map((u) => [u, u])],
                ["Firmatario", filterFirmatario, setFilterFirmatario, filterFirmatarioLogic, setFilterFirmatarioLogic, firmatariPreset.map((f) => [f, f])],
                ["Frazione", filterFrazione, setFilterFrazione, filterFrazioneLogic, setFilterFrazioneLogic, frazioniPreset.map((f) => [f, f])],
              ] as [string, string[], (v: string[]) => void, "and" | "or", (v: "and" | "or") => void, [string, string][]][]).map(([label, val, setVal, logic, setLogic, opts]) => (
                <div key={label} className="w-full md:flex-1 md:min-w-[110px] md:max-w-[180px]">
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">{label}</label>
                  <MultiSelectFilter label={label} options={opts} selected={val} onSelect={setVal} logic={logic} onLogicChange={setLogic} />
                </div>
              ))}
              <button onClick={resetFilters} className={`flex items-center justify-center col-span-2 md:col-span-1 gap-1 text-sm text-accent hover:underline md:mt-5 transition-opacity py-2 md:py-0 ${hasActiveFilters ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
                <X className="w-3.5 h-3.5" /> Azzera tutti
              </button>
            </div>
          )}

          {/* Badge filtri attivi */}
          {!imageMode && hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-border/50">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-widest mr-1">Filtri attivi:</span>

              {query && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-accent/10 text-accent border border-accent/20 rounded-full text-xs font-medium">
                  <span>Ricerca: "{query}"</span>
                  <button onClick={() => setQuery("")} className="hover:text-accent-foreground transition-colors"><X className="w-3 h-3" /></button>
                </div>
              )}

              {filterTipo.map(t => (
                <div key={`tipo-${t}`} className="flex items-start gap-1.5 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-xl text-xs font-medium max-w-full">
                  <span className="break-words flex-1 min-w-0">{t}</span>
                  <button onClick={() => setFilterTipo(prev => prev.filter(x => x !== t))} className="hover:text-primary/70 transition-colors mt-0.5 shrink-0"><X className="w-3 h-3" /></button>
                </div>
              ))}

              {filterAnno.map(a => (
                <div key={`anno-${a}`} className="flex items-start gap-1.5 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-xl text-xs font-medium max-w-full">
                  <span className="break-words flex-1 min-w-0">{a}</span>
                  <button onClick={() => setFilterAnno(prev => prev.filter(x => x !== a))} className="hover:text-primary/70 transition-colors mt-0.5 shrink-0"><X className="w-3 h-3" /></button>
                </div>
              ))}

              {filterUfficio.map(u => (
                <div key={`ufficio-${u}`} className="flex items-start gap-1.5 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-xl text-xs font-medium max-w-full">
                  <span className="break-words flex-1 min-w-0">{u}</span>
                  <button onClick={() => setFilterUfficio(prev => prev.filter(x => x !== u))} className="hover:text-primary/70 transition-colors mt-0.5 shrink-0"><X className="w-3 h-3" /></button>
                </div>
              ))}

              {filterFirmatario.map(f => (
                <div key={`firm-${f}`} className="flex items-start gap-1.5 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-xl text-xs font-medium max-w-full">
                  <span className="break-words flex-1 min-w-0">{f}</span>
                  <button onClick={() => setFilterFirmatario(prev => prev.filter(x => x !== f))} className="hover:text-primary/70 transition-colors mt-0.5 shrink-0"><X className="w-3 h-3" /></button>
                </div>
              ))}

              {filterFrazione.map(f => (
                <div key={`fraz-${f}`} className="flex items-start gap-1.5 px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded-xl text-xs font-medium max-w-full">
                  <span className="break-words flex-1 min-w-0">{f}</span>
                  <button onClick={() => setFilterFrazione(prev => prev.filter(x => x !== f))} className="hover:text-primary/70 transition-colors mt-0.5 shrink-0"><X className="w-3 h-3" /></button>
                </div>
              ))}
            </div>
          )}

          {/* Contatore Risultati Sempre Visibile con Seleziona Tutti a destra */}
          <div className={`flex items-center justify-end gap-4 ${(!imageMode && hasActiveFilters) ? "mt-2" : "mt-4 pt-2 border-t border-border/30"}`}>
            {filtered.length > 0 && (
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                <input 
                  type="checkbox" 
                  className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5 cursor-pointer"
                  checked={selectedDocs.size === filtered.length && filtered.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedDocs(new Set(filtered.map((item: any) => (item.documento || item).id)));
                    } else {
                      setSelectedDocs(new Set());
                    }
                  }}
                />
                Seleziona tutti
              </label>
            )}
            <div className="text-right text-xs text-muted-foreground font-mono">
              {filtered.length} document{filtered.length !== 1 ? "i" : "o"} trovat{filtered.length !== 1 ? "i" : "o"}
            </div>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p>Nessun documento trovato.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 p-1">
          {filtered.map((item: any) => {
            const doc = item.documento || item;
            const spiegazione = item.spiegazione_ia;
            return (
              <DocCard
                key={doc.id}
                doc={doc}
                spiegazione_ia={spiegazione}
                punteggio_similarita={item.punteggio_similarita}
                onClick={() => onSelectDoc(doc.id)}
                adminUnlocked={adminUnlocked}
                onEdit={onEdit}
                onDelete={onDelete}
                selected={selectedDocs.has(doc.id)}
                onSelectToggle={handleSelectToggle}
              />
            );
          })}
        </div>
      )}

      {selectedDocs.size > 0 && (
        <div className="fixed bottom-4 md:bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 sm:gap-3 bg-card/95 backdrop-blur-md border border-border shadow-2xl rounded-full px-4 sm:px-6 py-2.5 animate-in slide-in-from-bottom-5 w-max max-w-[95vw] overflow-x-auto whitespace-nowrap">
          <span className="text-xs sm:text-sm font-semibold bg-primary text-primary-foreground w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center shrink-0">{selectedDocs.size}</span>
          
          <button onClick={handleBulkExport} className="flex items-center gap-1.5 text-xs sm:text-sm font-medium hover:text-primary transition-colors border-r border-border pr-3 sm:pr-4 shrink-0">
            <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> <span className="hidden sm:inline">Esporta ZIP</span><span className="sm:hidden">Esporta</span>
          </button>
          {adminUnlocked && (
            <button onClick={handleBulkDelete} className="text-xs sm:text-sm font-medium text-red-500 hover:text-red-600 transition-colors border-r border-border pr-3 sm:pr-4 shrink-0 flex items-center gap-1">
              <Trash2 className="w-3.5 h-3.5 sm:hidden" />
              <span>Elimina</span>
            </button>
          )}
          <button onClick={() => setSelectedDocs(new Set())} className="text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors pl-1 shrink-0">
            Annulla
          </button>
        </div>
      )}
    </main>
  );
}

import { useState, useEffect } from "react";
import { ScanSearch, X, Plus } from "lucide-react";
import type { Doc, Tipologia } from "../types";
import { EMPTY_FORM } from "../data/mockData";
import { newId } from "../utils/helpers";
import { documentiService } from "../services/documentiService";
import { entitaService } from "../services/entitaService";
import { getImageUrl } from "../services/api";
import { useDialog } from "../contexts/DialogContext";
import { NewEntityDialog, MissingEntity } from "./NewEntityDialog";

interface DocFormModalProps {
  editDoc: Doc | null;
  tipiPreset: string[];
  ufficiPreset: string[];
  firmatariPreset: string[];
  frazioniPreset: string[];
  onSave: (doc: Doc) => void;
  onClose: () => void;
}

export function DocFormModal({ editDoc, tipiPreset, ufficiPreset, firmatariPreset, frazioniPreset, onSave, onClose }: DocFormModalProps) {
  const [formData, setFormData] = useState<Omit<Doc, "id">>(
    editDoc
      ? { nome: editDoc.nome, descrizione: editDoc.descrizione, tipologia: editDoc.tipologia, data: editDoc.data, data_scadenza: editDoc.data_scadenza, uffici: editDoc.uffici, firmatari: editDoc.firmatari, frazioni: editDoc.frazioni, url_immagine: editDoc.url_immagine, testo_estratto: editDoc.testo_estratto }
      : { ...EMPTY_FORM }
  );
  
  const [localTipi, setLocalTipi] = useState<string[]>(tipiPreset);
  const [localUffici, setLocalUffici] = useState<string[]>(ufficiPreset);
  const [localFirmatari, setLocalFirmatari] = useState<string[]>(firmatariPreset);
  const [localFrazioni, setLocalFrazioni] = useState<string[]>(frazioniPreset);

  const { showConfirm, showAlert } = useDialog();
  const [ocrPreview, setOcrPreview] = useState<string | undefined>(editDoc?.url_immagine ? getImageUrl(editDoc.url_immagine) : undefined);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [searchTipi, setSearchTipi] = useState("");
  const [searchUffici, setSearchUffici] = useState("");
  const [searchFirmatari, setSearchFirmatari] = useState("");
  const [searchFrazioni, setSearchFrazioni] = useState("");

  const [missingEntities, setMissingEntities] = useState<MissingEntity[]>([]);
  const [pendingOcrResult, setPendingOcrResult] = useState<any>(null);

  async function handleOcr(file: File) {
    setOcrPreview(URL.createObjectURL(file));
    setOcrLoading(true);
    try {
      const result = await documentiService.analyzeOcr(file);
      console.log("=== DEBUG OCR RESULT ===", result);
      
      // Sanitizza risultati OCR (rimuove spazi vuoti iniziali/finali) per evitare falsi negativi col DB
      if (result.tipologia) result.tipologia = result.tipologia.trim() as Tipologia;
      if (result.uffici) result.uffici = result.uffici.map(u => u.trim());
      if (result.firmatari) result.firmatari = result.firmatari.map(f => f.trim());
      if (result.frazioni) result.frazioni = result.frazioni.map(f => f.trim());
      
      // Controllo entità mancanti
      const missingTipi: MissingEntity[] = result.tipologia && !localTipi.includes(result.tipologia) ? [{ type: "tipologie", originalName: result.tipologia }] : [];
      const missingUffici: MissingEntity[] = (result.uffici || []).filter(u => !localUffici.includes(u)).map(u => ({ type: "uffici", originalName: u }));
      const missingFirmatari: MissingEntity[] = (result.firmatari || []).filter(f => !localFirmatari.includes(f)).map(f => ({ type: "firmatari", originalName: f }));
      const missingFrazioni: MissingEntity[] = (result.frazioni || []).filter(fr => !localFrazioni.includes(fr)).map(fr => ({ type: "frazioni", originalName: fr }));
      
      const allMissing = [...missingTipi, ...missingUffici, ...missingFirmatari, ...missingFrazioni];
      
      if (allMissing.length > 0) {
        setPendingOcrResult(result);
        setMissingEntities(allMissing);
        setOcrLoading(false);
        return; // Ci fermiamo qui. Il flusso riprenderà quando l'utente chiude la modale.
      }

      await applyOcrResult(result);
      setOcrLoading(false);
    } catch (err) {
      console.error("Errore durante l'analisi OCR:", err);
      alert("Si è verificato un errore durante l'estrazione OCR dell'immagine. Verifica che il backend sia in esecuzione.");
      setOcrLoading(false);
    }
  }

  async function applyOcrResult(result: any) {
    const replaceAction = await showConfirm(
      "Modalità Compilazione OCR", 
      "Scegli come inserire i dati estratti dall'immagine nei campi della scheda.",
      "Sostituisci",
      "Riempi vuoti"
    );

    if (replaceAction === null) {
      setOcrPreview(undefined);
      return;
    }

    setFormData((p) => {
      if (replaceAction === true) { // Sostituisci
        return {
          ...p,
          nome: result.nome || p.nome,
          descrizione: result.descrizione || p.descrizione,
          tipologia: (result.tipologia as Tipologia) || p.tipologia,
          data: result.data || p.data,
          data_scadenza: result.data_scadenza !== undefined ? result.data_scadenza : p.data_scadenza,
          uffici: result.uffici?.length ? result.uffici : p.uffici,
          firmatari: result.firmatari?.length ? result.firmatari : p.firmatari,
          frazioni: result.frazioni?.length ? result.frazioni : p.frazioni,
          url_immagine: result.url_immagine || p.url_immagine,
          testo_estratto: result.testo_estratto || p.testo_estratto
        };
      } else { // Riempi vuoti
        return {
          ...p,
          nome: (!p.nome || p.nome === EMPTY_FORM.nome) && result.nome ? result.nome : p.nome,
          descrizione: (!p.descrizione || p.descrizione === EMPTY_FORM.descrizione) && result.descrizione ? result.descrizione : p.descrizione,
          tipologia: (p.tipologia === EMPTY_FORM.tipologia || !p.tipologia) && result.tipologia ? (result.tipologia as Tipologia) : p.tipologia,
          data: (p.data === EMPTY_FORM.data || !p.data) && result.data ? result.data : p.data,
          data_scadenza: p.data_scadenza || result.data_scadenza || null,
          uffici: p.uffici.length === 0 && result.uffici ? result.uffici : p.uffici,
          firmatari: p.firmatari.length === 0 && result.firmatari ? result.firmatari : p.firmatari,
          frazioni: p.frazioni.length === 0 && result.frazioni ? result.frazioni : p.frazioni,
          url_immagine: p.url_immagine || result.url_immagine || "",
          testo_estratto: p.testo_estratto || result.testo_estratto || null
        };
      }
    });
  }

  const handleEntitiesResolved = async (resolved: Record<string, { original: string; final: string }[]>, deleted: Record<string, string[]>) => {
    // Aggiorna lo stato locale con i nuovi preset risolti
    if (resolved.tipologie?.length) setLocalTipi(prev => [...prev, ...resolved.tipologie.map(r => r.final)]);
    if (resolved.uffici?.length) setLocalUffici(prev => [...prev, ...resolved.uffici.map(r => r.final)]);
    if (resolved.firmatari?.length) setLocalFirmatari(prev => [...prev, ...resolved.firmatari.map(r => r.final)]);
    if (resolved.frazioni?.length) setLocalFrazioni(prev => [...prev, ...resolved.frazioni.map(r => r.final)]);

    // Costruiamo il result aggiornato (sostituendo i nomi vecchi con quelli nuovi o rimuovendo i deleted)
    const result = { ...pendingOcrResult };

    if (result.tipologia) {
      if (deleted.tipologie?.includes(result.tipologia)) result.tipologia = undefined;
      else if (resolved.tipologie?.length) result.tipologia = resolved.tipologie[0].final; // Assuming 1 tipologia
    }

    // Correzione: uniamo i valori scartando i vecchi e aggiungendo i risolti (final)
    const originalMissingUffici = missingEntities.filter(m => m.type === 'uffici').map(m => m.originalName);
    result.uffici = [
      ...((result.uffici || []) as string[]).filter(u => !originalMissingUffici.includes(u)),
      ...(resolved.uffici || []).map(r => r.final)
    ];

    const originalMissingFirmatari = missingEntities.filter(m => m.type === 'firmatari').map(m => m.originalName);
    result.firmatari = [
      ...((result.firmatari || []) as string[]).filter(u => !originalMissingFirmatari.includes(u)),
      ...(resolved.firmatari || []).map(r => r.final)
    ];

    const originalMissingFrazioni = missingEntities.filter(m => m.type === 'frazioni').map(m => m.originalName);
    result.frazioni = [
      ...((result.frazioni || []) as string[]).filter(u => !originalMissingFrazioni.includes(u)),
      ...(resolved.frazioni || []).map(r => r.final)
    ];

    setMissingEntities([]);
    setPendingOcrResult(null);
    await applyOcrResult(result);
  };

  async function handleSave() {
    if (!formData.url_immagine) {
      await showAlert("Immagine mancante", "Devi caricare l'immagine della prima pagina (scansione OCR) per poter salvare la scheda.");
      return;
    }
    if (!formData.nome || !formData.tipologia || !formData.data) {
      await showAlert("Dati mancanti", "Assicurati di aver inserito Nome, Tipologia e Data.");
      return;
    }

    if (await showConfirm("Conferma salvataggio", editDoc ? "Sei sicuro di voler salvare le modifiche a questo documento?" : "Sei sicuro di voler creare questo nuovo documento?")) {
      const data = { ...formData };
      onSave(editDoc ? { ...data, id: editDoc.id } : { ...data, id: newId() });
    }
  }

  return (
    <div className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-bold text-lg" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>{editDoc ? "Modifica scheda" : "Nuova scheda"}</h2>
          <button onClick={onClose} className="p-1 text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-6 grid grid-cols-2 gap-4">
          {/* OCR upload */}
          <div className="col-span-2 mb-1">
            <label className="block text-xs text-muted-foreground mb-2 uppercase tracking-wide">Carica immagine prima pagina (OCR)</label>
            {!ocrPreview ? (
              <label className="flex items-center gap-3 border-2 border-dashed border-primary/25 rounded-lg px-4 py-3 cursor-pointer hover:bg-secondary/40 transition-colors group" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleOcr(f); }}>
                <div className="w-8 h-8 rounded bg-secondary flex items-center justify-center flex-shrink-0 group-hover:bg-primary/10 transition-colors">
                  <ScanSearch className="w-4 h-4 text-primary/60" />
                </div>
                <div>
                  <p className="text-sm text-foreground font-medium">Trascina o <span className="text-primary">clicca per caricare</span></p>
                  <p className="text-xs text-muted-foreground">Il testo verrà estratto via OCR e i campi pre-compilati automaticamente</p>
                </div>
                <input type="file" accept="image/*,.pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleOcr(f); }} />
              </label>
            ) : (
              <div className="flex items-center gap-3 bg-secondary/40 border border-border rounded-lg p-3">
                <img src={ocrPreview} alt="preview" className="w-12 h-12 object-cover rounded border border-border flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  {ocrLoading
                    ? <span className="flex items-center gap-2 text-sm text-muted-foreground"><span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin inline-block flex-shrink-0" />Analisi OCR in corso…</span>
                    : <span className="text-sm text-green-700 font-medium">Campi pre-compilati dall&apos;OCR — verifica e correggi se necessario</span>
                  }
                </div>
                <button type="button" onClick={() => { setOcrPreview(null); setFormData({ ...EMPTY_FORM }); }} className="p-1 text-muted-foreground hover:text-accent transition-colors flex-shrink-0"><X className="w-4 h-4" /></button>
              </div>
            )}
          </div>


          <div>
            <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Data</label>
            <input type="date" value={formData.data} onChange={(e) => setFormData((p) => ({ ...p, data: e.target.value }))} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Scadenza <span className="normal-case">(opzionale)</span></label>
            <input type="date" value={formData.data_scadenza || ""} onChange={(e) => setFormData((p) => ({ ...p, data_scadenza: e.target.value }))} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Nome documento</label>
            <input value={formData.nome} onChange={(e) => setFormData((p) => ({ ...p, nome: e.target.value }))} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted-foreground uppercase tracking-wide">Tipologia</label>
              <input type="search" placeholder="Cerca..." value={searchTipi} onChange={(e) => setSearchTipi(e.target.value)} className="w-1/2 sm:w-1/3 bg-input-background border border-border rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {localTipi.filter(t => t.toLowerCase().includes(searchTipi.toLowerCase())).map((t, i) => (
                <button key={`${t}-${i}`} type="button" onClick={() => setFormData((p) => ({ ...p, tipologia: t as Tipologia }))}
                  className={`p-2 rounded-xl text-xs font-medium border transition-all duration-150 h-full min-h-[40px] flex items-center justify-center text-center leading-tight break-words ${formData.tipologia === t ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"}`}>{t}</button>
              ))}
            </div>
          </div>

          <div className="col-span-2">
            <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">Descrizione</label>
            <textarea value={formData.descrizione} onChange={(e) => setFormData((p) => ({ ...p, descrizione: e.target.value }))} rows={3} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted-foreground uppercase tracking-wide">Uffici coinvolti</label>
              <input type="search" placeholder="Cerca uffici..." value={searchUffici} onChange={(e) => setSearchUffici(e.target.value)} className="w-1/2 sm:w-1/3 bg-input-background border border-border rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {localUffici.filter(u => u.toLowerCase().includes(searchUffici.toLowerCase())).map((u, i) => {
                const active = formData.uffici.includes(u);
                return <button key={`${u}-${i}`} type="button" onClick={() => setFormData((p) => ({ ...p, uffici: active ? p.uffici.filter((x) => x !== u) : [...p.uffici, u] }))}
                  className={`p-2 rounded-xl text-xs font-medium border transition-all duration-150 h-full min-h-[40px] flex items-center justify-center text-center leading-tight break-words ${active ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"}`}>{u}</button>;
              })}
            </div>
            {formData.uffici.length > 0 && <p className="text-xs text-muted-foreground mt-1">Selezionati: {formData.uffici.join(", ")}</p>}
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted-foreground uppercase tracking-wide">Firmatari</label>
              <input type="search" placeholder="Cerca firmatari..." value={searchFirmatari} onChange={(e) => setSearchFirmatari(e.target.value)} className="w-1/2 sm:w-1/3 bg-input-background border border-border rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {localFirmatari.filter(f => f.toLowerCase().includes(searchFirmatari.toLowerCase())).map((f, i) => {
                const active = formData.firmatari.includes(f);
                return <button key={`${f}-${i}`} type="button" onClick={() => setFormData((p) => ({ ...p, firmatari: active ? p.firmatari.filter((x) => x !== f) : [...p.firmatari, f] }))}
                  className={`p-2 rounded-xl text-xs font-medium border transition-all duration-150 h-full min-h-[40px] flex items-center justify-center text-center leading-tight break-words ${active ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"}`}>{f}</button>;
              })}
            </div>
            {formData.firmatari.length > 0 && <p className="text-xs text-muted-foreground mt-1">Selezionati: {formData.firmatari.join(", ")}</p>}
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted-foreground uppercase tracking-wide">Frazioni interessate</label>
              <input type="search" placeholder="Cerca frazioni..." value={searchFrazioni} onChange={(e) => setSearchFrazioni(e.target.value)} className="w-1/2 sm:w-1/3 bg-input-background border border-border rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <button type="button" onClick={() => setFormData((p) => ({ ...p, frazioni: [] }))}
                className={`p-2 rounded-xl text-xs font-medium border transition-all duration-150 h-full min-h-[40px] flex items-center justify-center text-center leading-tight break-words ${formData.frazioni.length === 0 ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"}`}>
                Tutto il Comune
              </button>
              {localFrazioni.filter(f => f.toLowerCase().includes(searchFrazioni.toLowerCase())).map((f, i) => {
                const active = formData.frazioni.includes(f);
                return <button key={`${f}-${i}`} type="button" onClick={() => setFormData((p) => ({ ...p, frazioni: active ? p.frazioni.filter((x) => x !== f) : [...p.frazioni, f] }))}
                  className={`p-2 rounded-xl text-xs font-medium border transition-all duration-150 h-full min-h-[40px] flex items-center justify-center text-center leading-tight break-words ${active ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"}`}>{f}</button>;
              })}
            </div>
            {formData.firmatari.length > 0 && <p className="text-xs text-muted-foreground mt-1">Selezionati: {formData.firmatari.join(", ")}</p>}
          </div>

        </div>

        <div className="sticky bottom-0 z-10 flex items-center justify-end gap-3 px-6 py-4 border-t border-border mt-2 bg-muted/95 backdrop-blur-sm rounded-b-xl">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium border border-border text-foreground hover:bg-secondary/50 transition-colors bg-card shadow-sm">Annulla</button>
          <button onClick={handleSave} className="px-4 py-2 rounded-lg text-sm font-bold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm">
            {editDoc ? "Salva Modifiche" : "Crea Scheda"}
          </button>
        </div>
      </div>
      
      {missingEntities.length > 0 && (
        <NewEntityDialog 
          entities={missingEntities}
          onComplete={handleEntitiesResolved}
          onCancel={() => {
            setMissingEntities([]);
            setPendingOcrResult(null);
            setOcrPreview(undefined);
          }}
        />
      )}
    </div>
  );
}

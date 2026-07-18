import { useState, useEffect, useRef } from "react";
import { Shield, LogOut, Upload, Plus, X, Trash2, Bell, UploadCloud, Edit2, Eye, EyeOff, Loader2 } from "lucide-react";
import type { Doc } from "../types";
import { authService } from "../services/authService";
import { documentiService } from "../services/documentiService";
import { entitaService } from "../services/entitaService";
import { NewEntityDialog, MissingEntity } from "../components/NewEntityDialog";
import { useDialog } from "../contexts/DialogContext";
import { auditService, AuditLog } from "../services/auditService";


interface AdminViewProps {
  adminUnlocked: boolean;
  setAdminUnlocked: React.Dispatch<React.SetStateAction<boolean>>;
  setSolitaireOpen: React.Dispatch<React.SetStateAction<boolean>>;
  onAdd: () => void;
  ufficiPreset: string[];
  setUfficiPreset: React.Dispatch<React.SetStateAction<string[]>>;
  firmatariPreset: string[];
  setFirmatariPreset: React.Dispatch<React.SetStateAction<string[]>>;
  frazioniPreset: string[];
  setFrazioniPreset: React.Dispatch<React.SetStateAction<string[]>>;
  tipiPreset: string[];
  setTipiPreset: React.Dispatch<React.SetStateAction<string[]>>;
  docs: Doc[];
  setDocs: React.Dispatch<React.SetStateAction<Doc[]>>;
}

/** Schede della sezione configurazione. */
type ConfigTab = "tipologie" | "uffici" | "firmatari" | "frazioni" | "operatori" | "audit";

/**
 * Area riservata agli amministratori comunali.
 * Accesso protetto da PIN: "admin2025" sblocca il pannello.
 */
export function AdminView({ docs, setDocs, adminUnlocked, setAdminUnlocked, setSolitaireOpen, onAdd, ufficiPreset, setUfficiPreset, firmatariPreset, setFirmatariPreset, frazioniPreset, setFrazioniPreset, tipiPreset, setTipiPreset }: AdminViewProps) {
  const { showAlert, showConfirm, showPrompt } = useDialog();
  const [username, setUsername] = useState("");
  const [adminPin, setAdminPin] = useState("");
  const [adminError, setAdminError] = useState("");
  const [isForgotFlow, setIsForgotFlow] = useState(false);
  const [forgotMessage, setForgotMessage] = useState("");
  const [configTab, setConfigTab] = useState<ConfigTab>("tipologie");
  const [newTipo, setNewTipo] = useState("");
  const [newUfficio, setNewUfficio] = useState("");
  const [newFirmatario, setNewFirmatario] = useState("");
  const [newFrazione, setNewFrazione] = useState("");
  const [errTipo, setErrTipo] = useState(false);
  const [errUfficio, setErrUfficio] = useState(false);
  const [errFirmatario, setErrFirmatario] = useState(false);
  const [errFrazione, setErrFrazione] = useState(false);
  const [operatori, setOperatori] = useState<any[]>([]);
  const [newOpUsername, setNewOpUsername] = useState("");
  const [newOpEmail, setNewOpEmail] = useState("");
  const [searchOp, setSearchOp] = useState("");
  const [bulkMissingEntities, setBulkMissingEntities] = useState<MissingEntity[]>([]);
  const importRef = useRef<HTMLInputElement>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  
  const isSupremeAdmin = authService.getLoggedUsername() === "admin";

  useEffect(() => {
    if (adminUnlocked && isSupremeAdmin && configTab === "operatori") {
      fetchOperatori();
    }
  }, [adminUnlocked, isSupremeAdmin, configTab]);

  async function fetchOperatori() {
    try {
      const ops = await authService.getUsers();
      setOperatori(ops.filter(o => o.username !== "admin"));
    } catch (err: any) {
      console.error(err);
    }
  }

  async function loadDocs() {
    const ds = await documentiService.getDocumenti();
    setDocs(ds);
  }

  async function handleAddOperatore() {
    if (!newOpUsername || !newOpEmail) {
      await showAlert("Errore", "Username e Email sono obbligatori.");
      return;
    }
    try {
      await authService.createUser({ username: newOpUsername, email: newOpEmail });
      await showAlert("Successo", `Utente creato! Un'email di invito è stata inviata a ${newOpEmail}.`);
      setNewOpUsername("");
      setNewOpEmail("");
      fetchOperatori();
    } catch (err: any) {
      await showAlert("Errore", "Impossibile creare utente: " + err.message);
    }
  }

  async function handleRemoveOperatore(username: string) {
    if (await showConfirm("Attenzione", `Sei sicuro di voler eliminare l'operatore "${username}"?`)) {
      try {
        await authService.deleteUser(username);
        fetchOperatori();
      } catch (err: any) {
        await showAlert("Errore", "Impossibile eliminare utente: " + err.message);
      }
    }
  }

  async function handleLogin() {
    if (username === "pausacomunale" && adminPin === "") { setSolitaireOpen(true); setAdminPin(""); setUsername(""); return; }
    
    try {
      await authService.login(username, adminPin);
      setAdminUnlocked(true);
      setAdminPin("");
      setUsername("");
    } catch (err: any) {
      setAdminError(err.message || "Credenziali non valide.");
    }
  }

  async function handleForgotPassword() {
    if (!username) {
      setAdminError("Inserisci lo username per recuperare la password.");
      return;
    }
    setAdminError("");
    setForgotMessage("");
    try {
      const res = await authService.forgotPassword(username);
      setForgotMessage(res.message);
    } catch (err: any) {
      setAdminError(err.message || "Errore durante la richiesta.");
    }
  }

  async function processImportFile(file: File) {
    setIsImporting(true);
    try {
      const res = await documentiService.importBulk(file);
      await showAlert("Importazione Completata", res.messaggio);
      
      const missing = res.nuove_entita;
      if (missing && (missing.tipologie?.length || missing.uffici?.length || missing.firmatari?.length || missing.frazioni?.length)) {
          const allMissing: MissingEntity[] = [];
          if (missing.tipologie) missing.tipologie.forEach(x => allMissing.push({ type: "tipologie", originalName: x }));
          if (missing.uffici) missing.uffici.forEach(x => allMissing.push({ type: "uffici", originalName: x }));
          if (missing.firmatari) missing.firmatari.forEach(x => allMissing.push({ type: "firmatari", originalName: x }));
          if (missing.frazioni) missing.frazioni.forEach(x => allMissing.push({ type: "frazioni", originalName: x }));
          
          if (allMissing.length > 0) {
            setBulkMissingEntities(allMissing);
          }
      }
      loadDocs();
    } catch (err: any) {
      await showAlert("Errore", "Errore importazione: " + err.message);
    } finally {
      setIsImporting(false);
    }
  }

  const handleBulkEntitiesResolved = async (resolved: Record<string, { original: string; final: string }[]>, deleted: Record<string, string[]>) => {
    if (resolved.tipologie?.length) setTipiPreset(p => [...new Set([...p, ...resolved.tipologie.map(r => r.final)])]);
    if (resolved.uffici?.length) setUfficiPreset(p => [...new Set([...p, ...resolved.uffici.map(r => r.final)])]);
    if (resolved.firmatari?.length) setFirmatariPreset(p => [...new Set([...p, ...resolved.firmatari.map(r => r.final)])]);
    if (resolved.frazioni?.length) setFrazioniPreset(p => [...new Set([...p, ...resolved.frazioni.map(r => r.final)])]);
    
    try {
      await documentiService.bulkResolveEntities(resolved, deleted);
      await showAlert("Salvataggio Completato", "I documenti sono stati aggiornati con i nuovi nomi.");
      loadDocs();
    } catch (e: any) {
      await showAlert("Errore", "Impossibile aggiornare i documenti importati: " + e.message);
    }

    setBulkMissingEntities([]);
  };

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await processImportFile(file);
    e.target.value = "";
  }

  async function handleDropZip(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      await showAlert("Errore", "Per favore carica un file con estensione .zip");
      return;
    }
    await processImportFile(file);
  }

  async function addPreset(
    value: string,
    list: string[],
    setList: React.Dispatch<React.SetStateAction<string[]>>,
    setVal: React.Dispatch<React.SetStateAction<string>>,
    setErr: React.Dispatch<React.SetStateAction<boolean>>,
    apiCall?: (nome: string) => Promise<any>
  ) {
    const v = value.trim();
    if (!v) return;
    if (list.some((x) => x.toLowerCase() === v.toLowerCase())) { setErr(true); return; }
    try {
      if (apiCall) await apiCall(v);
      setList((p) => [...p, v]);
      setVal("");
      setErr(false);
    } catch (err) {
      await showAlert("Errore", "Errore aggiunta entità: " + err);
    }
  }

  async function removePreset(
    name: string,
    setList: React.Dispatch<React.SetStateAction<string[]>>,
    getApi?: () => Promise<{id: number, nome: string}[]>,
    deleteApi?: (id: number) => Promise<void>
  ) {
    try {
      if (getApi && deleteApi) {
        const items = await getApi();
        const target = items.find(i => i.nome === name);
        if (target) {
          if (await showConfirm("Attenzione", `Sei sicuro di voler eliminare "${name}"?`)) {
            await deleteApi(target.id);
            setList((p) => p.filter((x) => x !== name));
          }
          return;
        }
      }
      setList((p) => p.filter((x) => x !== name));
    } catch (err) {
      await showAlert("Errore", "Errore rimozione: " + err);
    }
  }

  async function editPreset(
    oldName: string,
    setList: React.Dispatch<React.SetStateAction<string[]>>,
    getApi?: () => Promise<{id: number, nome: string}[]>,
    updateApi?: (id: number, newName: string) => Promise<any>
  ) {
    try {
      if (!getApi || !updateApi) return;
      const newName = await showPrompt("Rinomina", `Stai rinominando "${oldName}". Inserisci il nuovo nome:`, oldName);
      if (!newName || newName.trim() === "" || newName.trim() === oldName) return;
      
      const cleanName = newName.trim();
      const items = await getApi();
      const target = items.find(i => i.nome === oldName);
      if (target) {
         await updateApi(target.id, cleanName);
         setList(p => p.map(x => x === oldName ? cleanName : x));
         
         // Ricarica i documenti per riflettere le modifiche a cascata
         const ds = await documentiService.getDocumenti();
         setDocs(ds);
      }
    } catch (err: any) {
      await showAlert("Errore", "Errore modifica entità: " + (err.message || err));
    }
  }

  async function handleTriggerScadenze() {
    try {
      const res = await authService.triggerExpirationCheck();
      await showAlert("Successo", res.message || "Controllo scadenze simulato con successo.");
    } catch (err: any) {
      await showAlert("Errore", "Errore durante la simulazione scadenze: " + err);
    }
  }

  if (!adminUnlocked) {
    return (
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="max-w-sm mx-auto mt-16 bg-card border border-border rounded-xl p-8 shadow-sm text-center">
          <Shield className="w-10 h-10 mx-auto mb-4 text-primary/30" />
          <h2 className="text-lg font-bold mb-1" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Area Amministrativa</h2>
          <p className="text-sm text-muted-foreground mb-6">Inserisci le credenziali per accedere.</p>
          {!isForgotFlow ? (
            <>
              <input type="text" value={username} onChange={(e) => { setUsername(e.target.value); setAdminError(""); }} onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
                placeholder="Username" className="w-full text-center text-sm bg-input-background border border-border rounded-lg px-4 py-2.5 mb-3 focus:outline-none focus:ring-2 focus:ring-ring" />
              
              <div className="relative mb-3 w-full">
                <input type={showPassword ? "text" : "password"} value={adminPin} onChange={(e) => { setAdminPin(e.target.value); setAdminError(""); }} onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
                  placeholder="Password" className="w-full text-center text-sm tracking-widest bg-input-background border border-border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground transition-colors">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {adminError && <p className="text-xs text-accent mb-3">{adminError}</p>}
              <button onClick={handleLogin} className="w-full bg-primary text-primary-foreground rounded-lg py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors mb-3">Accedi</button>
              <button onClick={() => { setIsForgotFlow(true); setAdminError(""); setForgotMessage(""); }} className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2">Hai dimenticato la password?</button>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-4">Inserisci il tuo username. Riceverai un'email con le istruzioni per il ripristino.</p>
              <input type="text" value={username} onChange={(e) => { setUsername(e.target.value); setAdminError(""); setForgotMessage(""); }} onKeyDown={(e) => { if (e.key === "Enter") handleForgotPassword(); }}
                placeholder="Username" className="w-full text-center text-sm bg-input-background border border-border rounded-lg px-4 py-2.5 mb-3 focus:outline-none focus:ring-2 focus:ring-ring" />
              {adminError && <p className="text-xs text-accent mb-3">{adminError}</p>}
              {forgotMessage && <p className="text-xs text-green-600 mb-3">{forgotMessage}</p>}
              <button onClick={handleForgotPassword} className="w-full bg-primary text-primary-foreground rounded-lg py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors mb-3">Invia link di ripristino</button>
              <button onClick={() => { setIsForgotFlow(false); setAdminError(""); setForgotMessage(""); }} className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2">Torna al login</button>
            </>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="w-full min-w-0 max-w-[1400px] mx-auto px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold tracking-wide order-1" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Area Amministrativa</h1>
        
        <div className="w-full sm:w-auto order-3 sm:order-2 flex-grow">
          <button onClick={handleTriggerScadenze} className="text-[10px] text-muted-foreground hover:text-primary transition-colors border border-border/50 bg-secondary/30 rounded px-2 py-0.5" title="Forza invio email per i documenti in scadenza">
            [Demo: Trigger Email Scadenze]
          </button>
        </div>

        <button onClick={() => { authService.logout(); setAdminUnlocked(false); }} className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-transparent hover:border-border rounded-lg transition-all shrink-0 order-2 sm:order-3" title="Esci">
          <LogOut className="w-4 h-4" />
          <span>Log out</span>
        </button>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div 
          onClick={onAdd}
          className="bg-card border border-border hover:border-primary/50 transition-colors rounded-xl p-8 shadow-sm flex flex-col items-center justify-center text-center gap-4 cursor-pointer group"
        >
          <div className="w-16 h-16 bg-primary/10 group-hover:bg-primary/20 transition-colors rounded-full flex items-center justify-center text-primary">
            <Plus className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-lg font-bold mb-1">Nuovo Documento</h2>
            <p className="text-sm text-muted-foreground">Clicca qui per compilare la scheda e archiviare un nuovo atto o provvedimento nel sistema.</p>
          </div>
        </div>
        
        <div 
          className={`bg-card border border-border transition-colors rounded-xl p-4 shadow-sm group ${isImporting ? 'opacity-70 cursor-wait' : 'cursor-pointer hover:border-primary/50'}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            if (isImporting) return;
            handleDropZip(e);
          }}
          onClick={(e) => {
            if (isImporting) return;
            if (e.target !== importRef.current) {
               importRef.current?.click();
            }
          }}
        >
          <div className="border-2 border-dashed border-border group-hover:border-primary/40 transition-colors rounded-lg flex flex-col items-center justify-center text-center gap-4 h-full p-6">
            <div className={`w-16 h-16 ${isImporting ? 'bg-primary/20 text-primary' : 'bg-secondary text-secondary-foreground'} rounded-full flex items-center justify-center`}>
              {isImporting ? <Loader2 className="w-8 h-8 animate-spin" /> : <Upload className="w-8 h-8" />}
            </div>
            <div className="flex flex-col items-center text-center">
              <h2 className="text-lg font-bold mb-1">{isImporting ? "Importazione in corso..." : "Importazione Massiva (ZIP)"}</h2>
              {!isImporting && (
                <>
                  <p className="text-sm text-muted-foreground mb-2">Trascina qui il tuo archivio <b>.zip</b> oppure clicca per selezionarlo.</p>
                  <p className="text-xs text-muted-foreground text-left max-w-xs mx-auto bg-muted/30 p-2 rounded border border-border">
                    <b>Istruzioni:</b> Inserisci nello ZIP un singolo file <code>dati.csv</code> (o <code>.json</code>) e <b>tutte le relative immagini</b>. Le immagini sono obbligatorie. File non supportati nello ZIP verranno ignorati.
                  </p>
                </>
              )}
            </div>
            <input ref={importRef} type="file" accept=".zip" className="hidden" onChange={handleImport} />
          </div>
        </div>


      </div>

      <h2 className="text-xl font-bold tracking-wide mb-4" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Configurazione Metadati</h2>
      <div className="bg-card border border-border rounded-xl shadow-sm">
        <div className="flex gap-1 bg-muted/60 border-b border-border px-4 pt-3 pb-0 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          {(
            isSupremeAdmin
              ? [ ["tipologie", "Tipologie"], ["uffici", "Uffici"], ["firmatari", "Firmatari"], ["frazioni", "Frazioni"], ["operatori", "Operatori"], ["audit", "Registro Attività"] ]
              : [ ["tipologie", "Tipologie"], ["uffici", "Uffici"], ["firmatari", "Firmatari"], ["frazioni", "Frazioni"] ]
          ).map(([key, label]) => (
            <button key={key} onClick={() => setConfigTab(key as ConfigTab)}
              className={`px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors -mb-px ${configTab === key ? "border-primary text-primary bg-card" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="p-4 sm:p-6">
          {configTab === "tipologie" && <PresetSection description="Categorie utilizzate per classificare i documenti." items={tipiPreset} onRemove={(t) => removePreset(t, setTipiPreset, entitaService.getTipologie, entitaService.deleteTipologia)} onEdit={(t) => editPreset(t, setTipiPreset, entitaService.getTipologie, entitaService.updateTipologia)} value={newTipo} onChange={(v) => { setNewTipo(v); setErrTipo(false); }} onAdd={() => addPreset(newTipo, tipiPreset, setTipiPreset, setNewTipo, setErrTipo, entitaService.addTipologia)} placeholder="Nuova tipologia…" error={errTipo} />}
          {configTab === "uffici" && <PresetSection description="Uffici selezionabili nelle schede documento." items={ufficiPreset} onRemove={(u) => removePreset(u, setUfficiPreset, entitaService.getUffici, entitaService.deleteUfficio)} onEdit={(u) => editPreset(u, setUfficiPreset, entitaService.getUffici, entitaService.updateUfficio)} value={newUfficio} onChange={(v) => { setNewUfficio(v); setErrUfficio(false); }} onAdd={() => addPreset(newUfficio, ufficiPreset, setUfficiPreset, setNewUfficio, setErrUfficio, entitaService.addUfficio)} placeholder="Nuovo ufficio…" error={errUfficio} />}
          {configTab === "firmatari" && <PresetSection description="Persone autorizzate a firmare i documenti." items={firmatariPreset} onRemove={(f) => removePreset(f, setFirmatariPreset, entitaService.getFirmatari, entitaService.deleteFirmatario)} onEdit={(f) => editPreset(f, setFirmatariPreset, entitaService.getFirmatari, entitaService.updateFirmatario)} value={newFirmatario} onChange={(v) => { setNewFirmatario(v); setErrFirmatario(false); }} onAdd={() => addPreset(newFirmatario, firmatariPreset, setFirmatariPreset, setNewFirmatario, setErrFirmatario, entitaService.addFirmatario)} placeholder="Nuovo firmatario…" error={errFirmatario} />}
          {configTab === "frazioni" && <PresetSection description="Frazioni selezionabili per localizzare i documenti." items={frazioniPreset} onRemove={(f) => removePreset(f, setFrazioniPreset, entitaService.getFrazioni, entitaService.deleteFrazione)} onEdit={(f) => editPreset(f, setFrazioniPreset, entitaService.getFrazioni, entitaService.updateFrazione)} value={newFrazione} onChange={(v) => { setNewFrazione(v); setErrFrazione(false); }} onAdd={() => addPreset(newFrazione, frazioniPreset, setFrazioniPreset, setNewFrazione, setErrFrazione, entitaService.addFrazione)} placeholder="Nuova frazione…" error={errFrazione} />}
          {configTab === "operatori" && isSupremeAdmin && (
            <div className="grid md:grid-cols-2 gap-8 items-start">
              <div className="bg-muted/30 p-4 sm:p-6 border border-border rounded-xl md:sticky md:top-4 min-w-0">
                <h3 className="text-sm font-bold mb-1">Invita Nuovo Operatore</h3>
                <p className="text-xs text-muted-foreground mb-4">L'operatore riceverà un'email con un link per scegliere la propria password (valido 2 ore).</p>
                <div className="flex flex-col gap-3 mb-4">
                  <input type="text" value={newOpUsername} onChange={(e) => setNewOpUsername(e.target.value)} placeholder="Username" className="bg-input-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-full" />
                  <input type="email" value={newOpEmail} onChange={(e) => setNewOpEmail(e.target.value)} placeholder="Email (Obbligatoria)" className="bg-input-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-full" />
                </div>
                <button onClick={handleAddOperatore} className="w-full bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors">Invia Invito</button>
              </div>

              <div className="bg-muted/30 p-4 sm:p-6 border border-border rounded-xl min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                  <div>
                    <h3 className="text-sm font-bold mb-1">Lista Operatori</h3>
                    <p className="text-xs text-muted-foreground">Gestisci gli account secondari (sotto-admin) che possono accedere all'area amministrativa.</p>
                  </div>
                </div>
                <input type="search" placeholder="Cerca operatore..." value={searchOp} onChange={(e) => setSearchOp(e.target.value)} className="w-full bg-input-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring mb-4" />
                <div className="flex flex-col gap-3">
                  {operatori.filter(op => op.username.toLowerCase().includes(searchOp.toLowerCase()) || op.email?.toLowerCase().includes(searchOp.toLowerCase())).map((op, i) => (
                    <div key={op.id || i} className="flex items-center justify-between p-3 border border-border rounded-lg bg-card group hover:border-primary/30 transition-colors gap-2">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{op.username}</div>
                        {op.email && <div className="text-xs text-muted-foreground truncate">{op.email}</div>}
                      </div>
                      <button onClick={() => handleRemoveOperatore(op.username)} className="p-2 text-muted-foreground hover:text-accent transition-colors opacity-50 group-hover:opacity-100 flex-shrink-0" title="Elimina">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  {operatori.filter(op => op.username.toLowerCase().includes(searchOp.toLowerCase()) || op.email?.toLowerCase().includes(searchOp.toLowerCase())).length === 0 && (
                    <div className="text-sm text-muted-foreground italic p-4 border border-dashed border-border rounded-lg text-center bg-card">Nessun sotto-admin trovato.</div>
                  )}
                </div>
              </div>
            </div>
          )}
          {configTab === "audit" && isSupremeAdmin && <AuditSection />}
        </div>
      </div>
      
      {bulkMissingEntities.length > 0 && (
        <NewEntityDialog
          entities={bulkMissingEntities}
          onComplete={handleBulkEntitiesResolved}
          onCancel={() => setBulkMissingEntities([])}
        />
      )}
    </main>
  );
}

/** Sezione riutilizzabile per gestire una lista di preset (aggiungi/rimuovi). */
interface PresetSectionProps {
  description: string;
  items: string[];
  onRemove: (item: string) => void;
  onEdit?: (item: string) => void;
  value: string;
  onChange: (v: string) => void;
  onAdd: () => void;
  placeholder: string;
  error: boolean;
}

function PresetSection({ description, items, onRemove, onEdit, value, onChange, onAdd, placeholder, error }: PresetSectionProps) {
  const [search, setSearch] = useState("");
  const filteredItems = items.filter(item => item.toLowerCase().includes(search.toLowerCase()));

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <p className="text-xs text-muted-foreground">{description}</p>
        <input type="search" placeholder="Cerca tra i presenti..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full sm:w-1/3 bg-input-background border border-border rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 mb-6">
        {filteredItems.map((item, i) => (
          <div key={`${item}-${i}`} className="flex items-center justify-between bg-card text-muted-foreground border border-border rounded-xl px-3 p-2 min-h-[40px] text-xs font-medium group hover:border-primary/40 transition-all duration-150">
            <span className="break-words flex-1 min-w-0">{item}</span>
            <div className="flex items-center gap-1 opacity-40 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
              {onEdit && (
                <button onClick={() => onEdit(item)} className="text-muted-foreground hover:text-primary transition-colors flex-shrink-0" title="Rinomina">
                  <Edit2 className="w-3 h-3" />
                </button>
              )}
              <button onClick={() => onRemove(item)} className="text-muted-foreground hover:text-accent transition-colors flex-shrink-0" title="Rimuovi">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
        {filteredItems.length === 0 && (
          <div className="col-span-full text-xs text-muted-foreground italic py-2">Nessun elemento trovato.</div>
        )}
      </div>

      <div className="w-full max-w-sm pt-4 border-t border-border/50">
        <div className="flex flex-col sm:flex-row gap-2">
          <input value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onAdd(); }} placeholder={placeholder}
            className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <button onClick={onAdd} className="w-full sm:w-auto px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center justify-center gap-1.5 shrink-0">
            <Plus className="w-4 h-4" /> Aggiungi
          </button>
        </div>
        {error && <p className="text-xs text-accent mt-1">Valore già presente</p>}
      </div>
    </>
  );
}

function AuditSection() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const { showAlert } = useDialog();

  useEffect(() => {
    async function loadLogs() {
      try {
        const data = await auditService.getLogs(500);
        setLogs(data);
      } catch (err: any) {
        showAlert("Errore", "Impossibile caricare il registro attività.");
      } finally {
        setLoading(false);
      }
    }
    loadLogs();
  }, []);

  if (loading) {
    return <div className="p-4 text-center text-sm text-muted-foreground">Caricamento log in corso...</div>;
  }

  const handleRowClick = (log: AuditLog) => {
    setSelectedLog(log);
  };

  return (
    <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
      <div className="p-4 border-b border-border bg-muted/30">
        <h3 className="text-sm font-bold">Registro Attività (Audit Log)</h3>
        <p className="text-xs text-muted-foreground">Cronologia delle azioni di creazione, modifica ed eliminazione effettuate nel sistema.</p>
      </div>
      <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-muted/50 text-xs uppercase sticky top-0 z-10 backdrop-blur-md">
            <tr>
              <th className="px-4 py-3 border-b border-border font-medium">Data e Ora</th>
              <th className="px-4 py-3 border-b border-border font-medium">Operatore</th>
              <th className="px-4 py-3 border-b border-border font-medium">Azione</th>
              <th className="px-4 py-3 border-b border-border font-medium">ID Target</th>
              <th className="px-4 py-3 border-b border-border font-medium w-full">Dettagli</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {logs.length > 0 ? logs.map(log => (
              <tr key={log.id} onClick={() => handleRowClick(log)} className="hover:bg-muted/20 transition-colors cursor-pointer">
                <td className="px-4 py-3 text-xs text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</td>
                <td className="px-4 py-3 font-medium text-xs">{log.username}</td>
                <td className="px-4 py-3 text-xs">
                  <span className={`px-2 py-0.5 rounded-full ${
                    log.action.includes("DELETE") ? "bg-red-100 text-red-700 border border-red-200" :
                    log.action.includes("CREATE") || log.action.includes("IMPORT") ? "bg-green-100 text-green-700 border border-green-200" :
                    "bg-blue-100 text-blue-700 border border-blue-200"
                  }`}>
                    {log.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground font-mono">{log.target_id || "-"}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground truncate max-w-xs" title={log.details || ""}>{log.details || "-"}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm italic">
                  Nessuna attività registrata.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedLog && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-card w-full max-w-lg rounded-2xl shadow-xl border border-border flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
              <h2 className="text-sm font-bold">Dettagli Operazione</h2>
              <button 
                onClick={() => setSelectedLog(null)}
                className="p-1 text-muted-foreground hover:bg-secondary rounded-md transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">Azione</span>
                  <span className={`px-2 py-0.5 rounded-full inline-block text-xs font-medium ${
                    selectedLog.action.includes("DELETE") ? "bg-red-100 text-red-700 border border-red-200" :
                    selectedLog.action.includes("CREATE") || selectedLog.action.includes("IMPORT") ? "bg-green-100 text-green-700 border border-green-200" :
                    "bg-blue-100 text-blue-700 border border-blue-200"
                  }`}>
                    {selectedLog.action}
                  </span>
                </div>
                <div>
                  <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">Operatore</span>
                  <span className="font-medium">{selectedLog.username}</span>
                </div>
                <div>
                  <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">Data e Ora</span>
                  <span>{new Date(selectedLog.timestamp).toLocaleString()}</span>
                </div>
                <div>
                  <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-1">Target ID</span>
                  <span className="font-mono text-xs">{selectedLog.target_id || "-"}</span>
                </div>
              </div>
              
              <div className="pt-4 border-t border-border">
                <span className="block text-xs text-muted-foreground uppercase tracking-wider mb-2">Dettagli completi</span>
                <div className="bg-muted/30 p-3 rounded-lg border border-border text-sm whitespace-pre-wrap font-mono">
                  {selectedLog.details || "Nessun dettaglio aggiuntivo registrato."}
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-border bg-muted/10 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

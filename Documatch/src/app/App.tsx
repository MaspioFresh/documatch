import { useState, useEffect } from "react";
import { Shield } from "lucide-react";
import logoDocuMatch from "@/imports/logo-documatch-1.png";
import type { Doc, View } from "./types";
import { HomeView } from "./views/HomeView";
import { DetailView } from "./views/DetailView";
import { AdminView } from "./views/AdminView";
import { ResetPasswordView } from "./views/ResetPasswordView";
import { SolitaireModal } from "./components/SolitaireModal";
import { DocFormModal } from "./components/DocFormModal";
import { authService } from "./services/authService";
import { documentiService } from "./services/documentiService";
import { entitaService } from "./services/entitaService";
import { useDialog } from "./contexts/DialogContext";

/**
 * Componente radice dell'applicazione DocuMatch.
 * Gestisce solo routing client-side (via stato `view`) e stato globale condiviso:
 * - docs: dataset principale, modificabile dall'admin
 * - preset (uffici, firmatari, frazioni, tipi): condivisi tra HomeView e AdminView
 *   in modo che le modifiche in configurazione si riflettano subito nei filtri
 * - solitaireOpen: easter egg attivabile da AdminView tramite PIN speciale
 *
 * Tutta la logica di UI specifica di ciascuna schermata vive nella view corrispondente.
 */
export default function App() {
  const { showAlert, showConfirm } = useDialog();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [view, setView] = useState<View>(() => {
    const path = window.location.pathname;
    if (path === "/admin" || path === "/login") return "admin";
    return "home";
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState("");

  const [adminUnlocked, setAdminUnlocked] = useState(authService.isAuthenticated());
  const [solitaireOpen, setSolitaireOpen] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editDoc, setEditDoc] = useState<Doc | null>(null);

  // Preset condivisi tra HomeView (filtri) e AdminView (configurazione)
  const [ufficiPreset, setUfficiPreset] = useState<string[]>([]);
  const [firmatariPreset, setFirmatariPreset] = useState<string[]>([]);
  const [frazioniPreset, setFrazioniPreset] = useState<string[]>([]);
  const [tipiPreset, setTipiPreset] = useState<string[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const [docsRes, ufficiRes, frazioniRes, tipiRes, firmatariRes] = await Promise.all([
          documentiService.getDocumenti(),
          entitaService.getUffici(),
          entitaService.getFrazioni(),
          entitaService.getTipologie(),
          entitaService.getFirmatari(),
        ]);
        
        setDocs(docsRes);
        setUfficiPreset(ufficiRes.map(u => u.nome));
        setFrazioniPreset(frazioniRes.map(f => f.nome));
        setTipiPreset(tipiRes.map(t => t.nome));
        setFirmatariPreset(firmatariRes.map(f => f.nome));
      } catch (err) {
        console.error("Failed to load initial data", err);
      }
    }
    loadData();

    // Gestione semplice del routing tramite hash per il ripristino password
    const hash = window.location.hash;
    if (hash.startsWith("#/reset-password")) {
      const urlParams = new URLSearchParams(hash.split("?")[1]);
      const token = urlParams.get("token");
      if (token) {
        setResetToken(token);
        setView("reset");
        // Puliamo l'URL
        window.history.replaceState(null, "", window.location.pathname);
      }
    }
  }, []);

  const selected = docs.find((d) => d.id === selectedId);

  const handleDeleteDoc = async (id: string) => {
    if (await showConfirm("Elimina Documento", "Sei sicuro di voler eliminare questa scheda? L'operazione non può essere annullata.")) {
      try {
        await documentiService.deleteDocumento(id);
        setDocs((p) => p.filter((d) => d.id !== id));
        if (selectedId === id) setView("home");
      } catch (e: any) {
        await showAlert("Errore", "Errore eliminazione: " + e.message);
      }
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col" style={{ fontFamily: "Inter, sans-serif" }}>

      {solitaireOpen && <SolitaireModal onClose={() => setSolitaireOpen(false)} />}
      
      {showForm && (
        <DocFormModal 
          editDoc={editDoc} 
          tipiPreset={tipiPreset} 
          ufficiPreset={ufficiPreset} 
          firmatariPreset={firmatariPreset} 
          frazioniPreset={frazioniPreset}
          onSave={async (doc) => {
            try {
              if (editDoc) {
                const updated = await documentiService.updateDocumento(editDoc.id, doc);
                setDocs((prev) => prev.map((d) => d.id === editDoc.id ? updated : d));
              } else {
                const created = await documentiService.createDocumento(doc);
                setDocs((prev) => [...prev, created]);
              }
              setShowForm(false);
              setEditDoc(null);
            } catch (err: any) {
              await showAlert("Errore", "Errore salvataggio: " + err.message);
            }
          }}
          onClose={() => { setShowForm(false); setEditDoc(null); }} 
        />
      )}

      <header className="bg-primary text-primary-foreground sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:py-3 flex items-center justify-between">
          <button onClick={() => setView("home")} className="flex items-center gap-3">
            <div className="w-10 h-10 sm:w-9 sm:h-9 bg-white rounded-lg flex items-center justify-center p-1 shrink-0">
              <img src={logoDocuMatch} alt="DocuMatch" className="w-full h-full object-contain" />
            </div>
            <div className="text-left">
              <div className="text-xl font-bold leading-tight tracking-wide" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>DocuMatch</div>
              <div className="text-[10px] text-white/50 leading-none tracking-widest uppercase hidden sm:block">Comune di Montalto Uffugo</div>
            </div>
          </button>
          <nav className="flex items-center gap-2">
            <button onClick={() => setView("home")} className={`px-3 py-2 sm:px-3 sm:py-1.5 text-sm rounded transition-colors flex items-center gap-1.5 ${view === "home" ? "bg-white/20 font-medium" : "hover:bg-white/10"}`}>
              <span className="hidden sm:inline">Archivio</span>
              <span className="sm:hidden font-semibold">Home</span>
            </button>
            <button onClick={() => setView("admin")} className={`flex items-center gap-1.5 px-3 py-2 sm:px-3 sm:py-1.5 text-sm rounded transition-colors ${view === "admin" ? "bg-white/20 font-medium" : "hover:bg-white/10"}`}>
              <Shield className="w-4 h-4 sm:w-3.5 sm:h-3.5" /> <span className="hidden sm:inline">Admin</span>
            </button>
          </nav>
        </div>
      </header>

      {view === "home" && (
        <HomeView
          docs={docs}
          ufficiPreset={ufficiPreset}
          firmatariPreset={firmatariPreset}
          frazioniPreset={frazioniPreset}
          tipiPreset={tipiPreset}
          onSelectDoc={(id) => { setSelectedId(id); setView("detail"); }}
          adminUnlocked={adminUnlocked}
          onEdit={(doc) => { setEditDoc(doc); setShowForm(true); }}
          onDelete={handleDeleteDoc}
          onRefresh={() => {
            documentiService.getDocumenti().then(setDocs).catch(e => console.error(e));
          }}
        />
      )}

      {view === "detail" && selected && (
        <DetailView
          doc={selected}
          allDocs={docs}
          onBack={() => setView("home")}
          onSelectDoc={(id) => setSelectedId(id)}
          adminUnlocked={adminUnlocked}
          onEdit={(doc) => { setEditDoc(doc); setShowForm(true); }}
          onDelete={handleDeleteDoc}
        />
      )}

      {view === "admin" && (
        <AdminView
          docs={docs}
          setDocs={setDocs}
          adminUnlocked={adminUnlocked}
          setAdminUnlocked={setAdminUnlocked}
          setSolitaireOpen={setSolitaireOpen}
          onAdd={() => { setEditDoc(null); setShowForm(true); }}
          ufficiPreset={ufficiPreset}
          setUfficiPreset={setUfficiPreset}
          firmatariPreset={firmatariPreset}
          setFirmatariPreset={setFirmatariPreset}
          frazioniPreset={frazioniPreset}
          setFrazioniPreset={setFrazioniPreset}
          tipiPreset={tipiPreset}
          setTipiPreset={setTipiPreset}
        />
      )}

      {view === "reset" && (
        <ResetPasswordView token={resetToken} onBack={() => setView("admin")} />
      )}

      <footer className="mt-auto border-t border-border py-10 sm:py-6 px-4 text-center text-sm text-muted-foreground bg-card/50">
        <p>Progetto d'esame: Sistemi Distribuiti e Cloud Computing (SDCC) — A.A. 2025/2026</p>
        <p className="mt-1">Studente: <span className="font-semibold text-foreground">Manuel Amodio</span> — Matricola: <span className="font-semibold text-foreground">276571</span></p>
      </footer>
    </div>
  );
}

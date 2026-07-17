import { useState, useEffect } from "react";
import { X, Check } from "lucide-react";
import { entitaService } from "../services/entitaService";

export interface MissingEntity {
  type: "tipologie" | "uffici" | "firmatari" | "frazioni";
  originalName: string;
}

interface NewEntityDialogProps {
  entities: MissingEntity[];
  onComplete: (resolved: Record<string, { original: string; final: string }[]>, deleted: Record<string, string[]>) => void;
  onCancel: () => void;
}

export function NewEntityDialog({ entities, onComplete, onCancel }: NewEntityDialogProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentName, setCurrentName] = useState("");
  
  const [resolvedEntities, setResolvedEntities] = useState<Record<string, { original: string; final: string }[]>>({
    tipologie: [], uffici: [], firmatari: [], frazioni: []
  });
  const [deletedEntities, setDeletedEntities] = useState<Record<string, string[]>>({
    tipologie: [], uffici: [], firmatari: [], frazioni: []
  });

  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (entities[currentIndex]) {
      setCurrentName(entities[currentIndex].originalName);
    }
  }, [currentIndex, entities]);

  if (entities.length === 0) {
    onComplete(resolvedEntities, deletedEntities);
    return null;
  }

  const currentEntity = entities[currentIndex];
  
  const typeLabels = {
    tipologie: "Tipologia",
    uffici: "Ufficio",
    firmatari: "Firmatario",
    frazioni: "Frazione"
  };

  const handleNext = async (action: "add" | "ignore") => {
    const finalName = currentName.trim() || currentEntity.originalName;
    
    if (action === "add") {
      setIsSaving(true);
      try {
        if (currentEntity.type === "tipologie") await entitaService.addTipologia(finalName);
        if (currentEntity.type === "uffici") await entitaService.addUfficio(finalName);
        if (currentEntity.type === "firmatari") await entitaService.addFirmatario(finalName);
        if (currentEntity.type === "frazioni") await entitaService.addFrazione(finalName);
        
        setResolvedEntities(prev => ({
          ...prev,
          [currentEntity.type]: [...prev[currentEntity.type], { original: currentEntity.originalName, final: finalName }]
        }));
      } catch (e: any) {
        alert("Errore durante il salvataggio dell'entità: " + e.message);
        setIsSaving(false);
        return; // Don't proceed on error
      }
      setIsSaving(false);
    } else {
      // Se ignorato, lo segniamo come eliminato
      setDeletedEntities(prev => ({
        ...prev,
        [currentEntity.type]: [...prev[currentEntity.type], currentEntity.originalName]
      }));
    }

    if (currentIndex + 1 < entities.length) {
      setCurrentIndex(prev => prev + 1);
    } else {
      // Completato
      onComplete(
        action === "add" 
          ? { ...resolvedEntities, [currentEntity.type]: [...resolvedEntities[currentEntity.type], { original: currentEntity.originalName, final: finalName }] } 
          : resolvedEntities,
        action === "ignore"
          ? { ...deletedEntities, [currentEntity.type]: [...deletedEntities[currentEntity.type], currentEntity.originalName] }
          : deletedEntities
      );
    }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
          <h2 className="font-bold text-lg" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Nuova Entità Trovata</h2>
          <button onClick={onCancel} className="p-1 text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          <p className="text-sm text-muted-foreground mb-4">
            L'Intelligenza Artificiale ha rilevato un valore non presente nel database per il campo <strong className="text-foreground">{typeLabels[currentEntity.type]}</strong>.
          </p>
          <div className="mb-6">
            <label className="block text-xs text-muted-foreground mb-1 uppercase tracking-wide">
              {typeLabels[currentEntity.type]} rilevato (Modificabile)
            </label>
            <input 
              value={currentName} 
              onChange={e => setCurrentName(e.target.value)}
              className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            />
            <p className="text-xs text-muted-foreground mt-2">
              Modifica il nome e clicca "Aggiungi" per salvarlo nelle anagrafiche. Se clicchi "Ignora", questa entità verrà rimossa dal documento importato.
            </p>
          </div>
          <div className="flex gap-3 justify-end">
            <button 
              onClick={() => handleNext("ignore")} 
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium border border-border rounded-lg text-muted-foreground hover:bg-secondary/40 transition-colors"
            >
              Ignora / Elimina
            </button>
            <button 
              onClick={() => handleNext("add")} 
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {isSaving ? "Salvataggio..." : <><Check className="w-4 h-4"/> Aggiungi</>}
            </button>
          </div>
          <div className="mt-4 flex gap-1 justify-center">
            {entities.map((_, i) => (
              <div key={i} className={`h-1.5 rounded-full ${i === currentIndex ? 'w-4 bg-primary' : i < currentIndex ? 'w-2 bg-primary/40' : 'w-2 bg-border'} transition-all`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

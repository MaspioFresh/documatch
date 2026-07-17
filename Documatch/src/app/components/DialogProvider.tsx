import { useState, useCallback } from "react";
import { DialogContext } from "../contexts/DialogContext";
import { AlertCircle, HelpCircle, CheckCircle, Edit3 } from "lucide-react";

interface DialogState {
  isOpen: boolean;
  type: "alert" | "confirm" | "prompt";
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  resolve: (value: any) => void;
}

export function DialogProvider({ children }: { children: React.ReactNode }) {
  const [dialog, setDialog] = useState<DialogState>({
    isOpen: false,
    type: "alert",
    title: "",
    message: "",
    resolve: () => {},
  });
  const [promptValue, setPromptValue] = useState("");

  const showAlert = useCallback((title: string, message: string) => {
    return new Promise<void>((resolve) => {
      setDialog({
        isOpen: true,
        type: "alert",
        title,
        message,
        resolve: (value) => resolve(),
      });
    });
  }, []);

  const showConfirm = useCallback((title: string, message: string, confirmText?: string, cancelText?: string) => {
    return new Promise<boolean | null>((resolve) => {
      setDialog({
        isOpen: true,
        type: "confirm",
        title,
        message,
        confirmText,
        cancelText,
        resolve,
      });
    });
  }, []);

  const showPrompt = useCallback((title: string, message: string, defaultValue?: string) => {
    return new Promise<string | null>((resolve) => {
      setPromptValue(defaultValue || "");
      setDialog({
        isOpen: true,
        type: "prompt",
        title,
        message,
        resolve,
      });
    });
  }, []);

  const handleClose = (value: any) => {
    setDialog((prev) => ({ ...prev, isOpen: false }));
    dialog.resolve(value);
  };

  return (
    <DialogContext.Provider value={{ showAlert, showConfirm, showPrompt }}>
      {children}
      
      {dialog.isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card w-full max-w-sm rounded-xl shadow-xl overflow-hidden border border-border animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 text-center">
              {dialog.type === "alert" ? (
                dialog.title.toLowerCase().includes("successo") || dialog.title.toLowerCase().includes("completat") || dialog.title.toLowerCase().includes("ok") ? (
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 text-accent/80" />
                )
              ) : dialog.type === "prompt" ? (
                <Edit3 className="w-12 h-12 mx-auto mb-4 text-primary/80" />
              ) : (
                <HelpCircle className="w-12 h-12 mx-auto mb-4 text-primary/80" />
              )}
              <h2 className="text-xl font-bold mb-2 text-foreground" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>
                {dialog.title}
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                {dialog.message}
              </p>
              
              {dialog.type === "prompt" && (
                <input
                  type="text"
                  value={promptValue}
                  onChange={(e) => setPromptValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleClose(promptValue); }}
                  className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring mb-6 text-center"
                  autoFocus
                />
              )}

              <div className="flex items-center justify-center gap-3 mt-2">
                {(dialog.type === "confirm" || dialog.type === "prompt") && (
                  <button
                    onClick={() => handleClose(false)}
                    className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
                  >
                    {dialog.cancelText || "Annulla"}
                  </button>
                )}
                <button
                  onClick={() => handleClose(dialog.type === "prompt" ? promptValue : true)}
                  className={`flex-1 px-4 py-2 text-primary-foreground rounded-lg text-sm font-medium transition-colors bg-primary hover:bg-primary/90`}
                >
                  {dialog.type === "alert" ? "Chiudi" : (dialog.type === "prompt" ? "Salva" : (dialog.confirmText || "Conferma"))}
                </button>
              </div>
              {dialog.type === "confirm" && dialog.cancelText && dialog.cancelText !== "Annulla" && (
                <button onClick={() => handleClose(null)} className="mt-4 text-xs text-muted-foreground hover:text-foreground underline underline-offset-2">
                  Annulla operazione
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </DialogContext.Provider>
  );
}

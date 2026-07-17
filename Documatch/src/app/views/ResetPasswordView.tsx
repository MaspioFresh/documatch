import { useState } from "react";
import { KeyRound, ShieldAlert, ShieldCheck, Eye, EyeOff } from "lucide-react";
import { authService } from "../services/authService";
import zxcvbn from "zxcvbn";
import type { View } from "../types";

interface ResetPasswordViewProps {
  token: string;
  onBack: () => void;
}

export function ResetPasswordView({ token, onBack }: ResetPasswordViewProps) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  async function handleReset() {
    if (!password || !confirmPassword) {
      setError("Inserisci e conferma la nuova password.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Le password non coincidono.");
      return;
    }
    const score = zxcvbn(password).score;
    if (score < 3) {
      setError("La password è troppo debole. Aumenta la complessità.");
      return;
    }
    
    setError("");
    setLoading(true);
    
    try {
      await authService.resetPassword(token, password);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || "Errore durante il reset della password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <div className="max-w-sm mx-auto mt-16 bg-card border border-border rounded-xl p-8 shadow-sm text-center">
        <KeyRound className="w-10 h-10 mx-auto mb-4 text-primary/30" />
        <h2 className="text-lg font-bold mb-1" style={{ fontFamily: "Barlow Condensed, sans-serif" }}>Ripristina Password</h2>
        
        {success ? (
          <>
            <p className="text-sm text-green-600 mb-6 mt-2">Password aggiornata con successo! Ora puoi effettuare l'accesso.</p>
            <button onClick={onBack} className="w-full bg-primary text-primary-foreground rounded-lg py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors">Torna al Login</button>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-6">Inserisci la tua nuova password.</p>
            <div className="relative mb-2 w-full">
              <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => { setPassword(e.target.value); setError(""); }} onKeyDown={(e) => { if (e.key === "Enter") handleReset(); }}
                placeholder="Nuova Password" className="w-full text-center text-sm tracking-widest bg-input-background border border-border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground transition-colors">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            
            {password && (() => {
              const score = zxcvbn(password).score;
              const colors = ["bg-red-500", "bg-red-400", "bg-orange-500", "bg-yellow-500", "bg-green-500"];
              const labels = ["Molto debole", "Debole", "Sufficiente", "Buona", "Eccellente"];
              return (
                <div className="mb-4 text-left">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground">Sicurezza: {labels[score]}</span>
                    {score >= 3 ? <ShieldCheck className="w-3 h-3 text-green-500" /> : <ShieldAlert className="w-3 h-3 text-red-500" />}
                  </div>
                  <div className="flex gap-1 h-1.5 w-full">
                    {[0, 1, 2, 3].map((idx) => (
                      <div key={idx} className={`h-full flex-1 rounded-full ${score > idx ? colors[score] : "bg-muted"}`} />
                    ))}
                  </div>
                  {score < 3 && <p className="text-[10px] text-muted-foreground mt-1">Usa lettere (maiuscole/minuscole), numeri e simboli.</p>}
                </div>
              );
            })()}

            <div className="relative mb-3 w-full">
              <input type={showConfirmPassword ? "text" : "password"} value={confirmPassword} onChange={(e) => { setConfirmPassword(e.target.value); setError(""); }} onKeyDown={(e) => { if (e.key === "Enter") handleReset(); }}
                placeholder="Conferma Password" className="w-full text-center text-sm tracking-widest bg-input-background border border-border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring" />
              <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground transition-colors">
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            
            {error && <p className="text-xs text-accent mb-3">{error}</p>}
            
            <button onClick={handleReset} disabled={loading || (password.length > 0 && zxcvbn(password).score < 3)} className="w-full bg-primary text-primary-foreground rounded-lg py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors mb-3 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? "Aggiornamento..." : "Salva nuova password"}
            </button>
            <button onClick={onBack} className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2">Annulla</button>
          </>
        )}
      </div>
    </main>
  );
}

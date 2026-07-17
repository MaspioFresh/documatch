interface SolitaireModalProps {
  onClose: () => void;
}

/**
 * Easter egg attivato digitando "pausacomunale" come PIN admin.
 * Carica il solitario di online-solitaire.com in un iframe a schermo intero.
 * sandbox="allow-scripts allow-same-origin" è il minimo necessario
 * per far girare il gioco; allow-popups è omesso intenzionalmente.
 */

export function SolitaireModal({
  onClose,
}: SolitaireModalProps) {
  return (
    <div className="fixed inset-0 z-[9999] flex flex-col bg-[#076324]">
      <div className="flex items-center justify-between px-5 py-3 bg-black/20">
        <span
          className="text-white font-semibold text-sm"
          style={{ fontFamily: "Barlow Condensed, sans-serif" }}
        >
          🃏 Pausa Comunale
        </span>
        <button
          onClick={onClose}
          className="text-white/70 hover:text-white text-xs border border-white/30 hover:border-white/60 rounded px-3 py-1 transition-colors"
        >
          Torna al lavoro
        </button>
      </div>
      <iframe
        src="https://online-solitaire.com/"
        className="flex-1 w-full border-none"
        title="Solitario"
        sandbox="allow-scripts allow-same-origin allow-forms"
      />
    </div>
  );
}
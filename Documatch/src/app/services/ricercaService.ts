import { apiFetch } from './api';
import type { Doc, RisultatoRicerca } from '../types';

export const ricercaService = {
  ricercaTestuale: (
    queryTesto: string,
    filtri: {
      tipologia?: string[];
      tipologia_logic?: "and" | "or";
      ufficio?: string[];
      ufficio_logic?: "and" | "or";
      firmatario?: string[];
      firmatario_logic?: "and" | "or";
      frazione?: string[];
      frazione_logic?: "and" | "or";
      data_inizio?: string;
      data_fine?: string;
    } = {}
  ): Promise<RisultatoRicerca[]> => {
    const params = new URLSearchParams();
    if (queryTesto) params.append('query_testo', queryTesto);
    
    if (filtri.tipologia?.length) { filtri.tipologia.forEach(t => params.append('tipologia', t)); if (filtri.tipologia_logic) params.append('tipologia_logic', filtri.tipologia_logic); }
    if (filtri.ufficio?.length) { filtri.ufficio.forEach(u => params.append('ufficio', u)); if (filtri.ufficio_logic) params.append('ufficio_logic', filtri.ufficio_logic); }
    if (filtri.firmatario?.length) { filtri.firmatario.forEach(f => params.append('firmatario', f)); if (filtri.firmatario_logic) params.append('firmatario_logic', filtri.firmatario_logic); }
    if (filtri.frazione?.length) { filtri.frazione.forEach(f => params.append('frazione', f)); if (filtri.frazione_logic) params.append('frazione_logic', filtri.frazione_logic); }
    
    if (filtri.data_inizio) params.append('data_inizio', filtri.data_inizio);
    if (filtri.data_fine) params.append('data_fine', filtri.data_fine);

    return apiFetch(`/api/v1/documents/search?${params.toString()}`);
  },

  ricercaImmagine: (file: File): Promise<{ testo_estratto_ocr: string; corrispondenze: RisultatoRicerca[] }> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/api/v1/documents/search-by-image', {
      method: 'POST',
      body: formData
    });
  }
};

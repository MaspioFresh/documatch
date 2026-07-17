import { apiFetch } from './api';
import type { Doc } from '../types';

export const documentiService = {
  getDocumenti: (): Promise<Doc[]> => {
    return apiFetch('/api/v1/documents/');
  },
  
  getDocumento: (id: string): Promise<Doc> => {
    return apiFetch(`/api/v1/documents/${id}`);
  },
  
  createDocumento: (payload: Omit<Doc, 'id'>): Promise<Doc> => {
    return apiFetch('/api/v1/documents/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  
  updateDocumento: (id: string, payload: Omit<Doc, 'id'>): Promise<Doc> => {
    return apiFetch(`/api/v1/documents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
  },
  
  deleteDocumento: (id: string): Promise<void> => {
    return apiFetch(`/api/v1/documents/${id}`, {
      method: 'DELETE'
    });
  },
  
  importBulk: async (file: File): Promise<{ status: string; messaggio: string; documenti_importati: number; nuove_entita?: Record<string, string[]> }> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/api/v1/documents/import-bulk', {
      method: 'POST',
      body: formData,
    });
  },
  
  analyzeOcr: (file: File): Promise<Partial<Doc>> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/api/v1/documents/analyze-ocr', {
      method: 'POST',
      body: formData
    });
  },
  
  getRecommendations: (id: string): Promise<{ documento: Doc; punteggio_similarita: number; spiegazione_ia: string }[]> => {
    return apiFetch(`/api/v1/documents/${id}/recommendations`);
  },

  exportBulk: async (ids: string[], format: "json" | "csv" = "json"): Promise<void> => {
    const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
    const token = localStorage.getItem('documatch_token');
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${BASE_URL}/api/v1/documents/export-bulk`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ids, format })
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Errore durante l'esportazione");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Nome file: exportGG-MM-AAAA.zip
    const dateStr = new Date().toLocaleDateString('it-IT').replace(/\//g, '-');
    a.download = `export${dateStr}.zip`;
    
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
  
  bulkDelete: (ids: string[]): Promise<{ status: string; messaggio: string }> => {
    return apiFetch('/api/v1/documents/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ ids })
    });
  },

  bulkResolveEntities: (resolved: Record<string, { original: string; final: string }[]>, deleted: Record<string, string[]>): Promise<void> => {
    return apiFetch('/api/v1/documents/bulk-resolve-entities', {
      method: 'POST',
      body: JSON.stringify({ resolved, deleted })
    });
  }
};

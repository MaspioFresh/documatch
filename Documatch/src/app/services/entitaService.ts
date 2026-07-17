import { apiFetch } from './api';

export interface Entita {
  id: number;
  nome: string;
}

export const entitaService = {
  // Tipologie
  getTipologie: (): Promise<Entita[]> => apiFetch('/api/v1/typologies/'),
  addTipologia: (nome: string): Promise<Entita> => apiFetch('/api/v1/typologies/', { method: 'POST', body: JSON.stringify({ nome }) }),
  updateTipologia: (id: number, nome: string): Promise<Entita> => apiFetch(`/api/v1/typologies/${id}`, { method: 'PUT', body: JSON.stringify({ nome }) }),
  deleteTipologia: (id: number): Promise<void> => apiFetch(`/api/v1/typologies/${id}`, { method: 'DELETE' }),

  // Uffici
  getUffici: (): Promise<Entita[]> => apiFetch('/api/v1/offices/'),
  addUfficio: (nome: string): Promise<Entita> => apiFetch('/api/v1/offices/', { method: 'POST', body: JSON.stringify({ nome }) }),
  updateUfficio: (id: number, nome: string): Promise<Entita> => apiFetch(`/api/v1/offices/${id}`, { method: 'PUT', body: JSON.stringify({ nome }) }),
  deleteUfficio: (id: number): Promise<void> => apiFetch(`/api/v1/offices/${id}`, { method: 'DELETE' }),

  // Frazioni
  getFrazioni: (): Promise<Entita[]> => apiFetch('/api/v1/frazioni/'),
  addFrazione: (nome: string): Promise<Entita> => apiFetch('/api/v1/frazioni/', { method: 'POST', body: JSON.stringify({ nome }) }),
  updateFrazione: (id: number, nome: string): Promise<Entita> => apiFetch(`/api/v1/frazioni/${id}`, { method: 'PUT', body: JSON.stringify({ nome }) }),
  deleteFrazione: (id: number): Promise<void> => apiFetch(`/api/v1/frazioni/${id}`, { method: 'DELETE' }),

  // Firmatari
  getFirmatari: (): Promise<Entita[]> => apiFetch('/api/v1/firmatari/'),
  addFirmatario: (nome: string): Promise<Entita> => apiFetch('/api/v1/firmatari/', { method: 'POST', body: JSON.stringify({ nome }) }),
  updateFirmatario: (id: number, nome: string): Promise<Entita> => apiFetch(`/api/v1/firmatari/${id}`, { method: 'PUT', body: JSON.stringify({ nome }) }),
  deleteFirmatario: (id: number): Promise<void> => apiFetch(`/api/v1/firmatari/${id}`, { method: 'DELETE' })
};

import { apiFetch } from './api';
import type { Doc } from '../types';

export const chatService = {
  chiediAlChatbot: (message: string, document_id?: string, history: any[] = []): Promise<{ response: string; sources: Doc[] }> => {
    return apiFetch('/api/v1/chat/', {
      method: 'POST',
      body: JSON.stringify({ message, document_id, history })
    });
  }
};

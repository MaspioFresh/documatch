import { apiFetch } from './api';

export interface AuditLog {
  id: number;
  timestamp: string;
  username: string;
  action: string;
  target_id: string | null;
  details: string | null;
}

export const auditService = {
  getLogs: async (limit: number = 100): Promise<AuditLog[]> => {
    return apiFetch(`/api/v1/audit/?limit=${limit}`);
  }
};

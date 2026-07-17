import { apiFetch } from './api';
import type { User } from '../types';

export const authService = {
  getToken: () => sessionStorage.getItem('documatch_token'),
  getLoggedUsername: () => sessionStorage.getItem('documatch_username'),
  
  isAuthenticated: () => !!sessionStorage.getItem('documatch_token'),
  
  login: async (username: string, password: string): Promise<User> => {
    const response = await apiFetch('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    sessionStorage.setItem('documatch_token', response.access_token);
    sessionStorage.setItem('documatch_username', response.username);
    return { username: response.username, is_admin: response.username === 'admin' };
  },

  logout: () => {
    sessionStorage.removeItem('documatch_token');
    sessionStorage.removeItem('documatch_username');
  },

  forgotPassword: async (username: string): Promise<{ message: string }> => {
    return apiFetch('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ username }),
    });
  },

  resetPassword: async (token: string, password: string): Promise<{ message: string }> => {
    return apiFetch('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, password }),
    });
  },

  getUsers: async (): Promise<any[]> => {
    return apiFetch('/api/v1/auth/users');
  },

  createUser: async (payload: any): Promise<any> => {
    return apiFetch('/api/v1/auth/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  deleteUser: async (username: string): Promise<any> => {
    return apiFetch(`/api/v1/auth/users/${username}`, {
      method: 'DELETE',
    });
  },

  triggerExpirationCheck: async (): Promise<{ message: string }> => {
    return apiFetch('/api/v1/auth/trigger-expiration-check', {
      method: 'POST',
    });
  }
};

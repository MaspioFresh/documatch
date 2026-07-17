const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = sessionStorage.getItem('documatch_token');
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Se inviamo FormData (es. upload file), il browser deve impostare il Content-Type
  // automaticamente per includere il boundary corretto.
  if (options.body instanceof FormData) {
    delete (headers as Record<string, string>)['Content-Type'];
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !path.includes('/auth/login')) {
    // Unauthorized: token scaduto o non valido
    sessionStorage.removeItem('documatch_token');
    window.location.reload();
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API error: ${response.status}`);
  }

  // Per richieste DELETE o senza body
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export function getImageUrl(path: string | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith('http')) return path;
  
  // Rimuoviamo "/api/v1" dal BASE_URL perché le immagini sono servite alla root in /static/
  const serverUrl = BASE_URL.replace(/\/api\/v1\/?$/, '');
  return `${serverUrl}${path}`;
}

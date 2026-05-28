import axios from 'axios';
import type {
  Mailbox, Group, PaginatedResponse, ImportResult,
  EmailSummary, EmailDetail, TokenStatus,
} from '@/types';

const http = axios.create({ baseURL: '/api', withCredentials: true });

http.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401) {
      window.dispatchEvent(new Event('app:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export const groupsApi = {
  list: () => http.get<Group[]>('/groups').then(r => r.data),
  create: (data: { name: string; description?: string }) =>
    http.post<Group>('/groups', data).then(r => r.data),
  update: (id: string, data: { name?: string; description?: string }) =>
    http.put<Group>(`/groups/${id}`, data).then(r => r.data),
  delete: (id: string) => http.delete(`/groups/${id}`),
};

export const mailboxesApi = {
  list: (params: { page?: number; page_size?: number; search?: string; group_id?: string }) =>
    http.get<PaginatedResponse<Mailbox>>('/mailboxes', { params }).then(r => r.data),
  import: (items: { email: string; password: string; client_id: string; refresh_token: string }[], mode: string) =>
    http.post<ImportResult>('/mailboxes/import', { items, mode }).then(r => r.data),
  export: (data: { ids?: string[]; format: string; include_all?: boolean }) =>
    http.post('/mailboxes/export', data, { responseType: 'blob' }),
  delete: (id: string) => http.delete(`/mailboxes/${id}`),
  batchDelete: (ids: string[]) =>
    http.request({ method: 'DELETE', url: '/mailboxes/batch', data: { ids } }).then(r => r.data),
  batchSetGroup: (ids: string[], group_id: string | null) =>
    http.patch('/mailboxes/batch/group', { ids, group_id }).then(r => r.data),
  batchCopy: (ids: string[], type: 'email' | 'password' | 'combined') =>
    http.post<{ text: string }>('/mailboxes/batch/copy', { ids, type }).then(r => r.data),
};

export const emailsApi = {
  list: (mailboxId: string, params: { folder?: string; page?: number; page_size?: number; search?: string }) =>
    http.get<EmailSummary[]>(`/mailboxes/${mailboxId}/emails`, { params }).then(r => r.data),
  detail: (mailboxId: string, messageId: string) =>
    http.get<EmailDetail>(`/mailboxes/${mailboxId}/emails/${messageId}`).then(r => r.data),
};

export const tokensApi = {
  status: (ids: string[]) =>
    http.get<TokenStatus[]>('/tokens/status', { params: { ids: ids.join(',') } }).then(r => r.data),
  check: (ids: string[]) =>
    http.post('/tokens/check', { ids }).then(r => r.data),
};

export const authApi = {
  unlock: (password: string) =>
    http.post<{ ok: boolean }>('/auth/unlock', { password }).then(r => r.data),
  status: () =>
    http.get<{ unlocked: boolean }>('/auth/status').then(r => r.data),
  logout: () =>
    http.post<{ ok: boolean }>('/auth/logout').then(r => r.data),
};

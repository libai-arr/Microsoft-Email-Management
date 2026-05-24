export interface Mailbox {
  id: string;
  email: string;
  group_id: string | null;
  group_name: string | null;
  token_status: 'normal' | 'checking' | 'expired';
  channel: string;
  token_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Group {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  mailbox_count: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  total: number;
}

export interface EmailSummary {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  preview: string;
  received_at: string;
  is_read: boolean;
  folder?: string;
}

export interface EmailDetail {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  received_at: string;
  body_html: string;
}

export interface TokenStatus {
  id: string;
  status: 'normal' | 'checking' | 'expired';
  checked_at: string | null;
}

import { useState, useCallback } from 'react';
import { message } from 'antd';
import { emailsApi } from '@/services/api';
import type { EmailSummary, EmailDetail } from '@/types';

export function useEmails(mailboxId: string) {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchList = useCallback(async (params: {
    folder?: string; page?: number; search?: string;
  } = {}) => {
    setLoading(true);
    try {
      const result = await emailsApi.list(mailboxId, params);
      setEmails(result);
    } catch (error: any) {
      setEmails([]);
      message.error(error?.response?.data?.detail || '获取邮件列表失败');
    } finally {
      setLoading(false);
    }
  }, [mailboxId]);

  const fetchDetail = useCallback(async (messageId: string) => {
    setLoading(true);
    try {
      const result = await emailsApi.detail(mailboxId, messageId);
      setDetail(result);
    } catch (error: any) {
      setDetail(null);
      message.error(error?.response?.data?.detail || '获取邮件详情失败');
    } finally {
      setLoading(false);
    }
  }, [mailboxId]);

  return { emails, detail, loading, fetchList, fetchDetail };
}

import { useState, useCallback } from 'react';
import { mailboxesApi } from '@/services/api';
import type { Mailbox, PaginatedResponse } from '@/types';

export function useMailboxes() {
  const [data, setData] = useState<PaginatedResponse<Mailbox>>({
    total: 0, page: 1, page_size: 10, items: [],
  });
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async (params: {
    page?: number; page_size?: number; search?: string; group_id?: string;
  } = {}) => {
    setLoading(true);
    try {
      const result = await mailboxesApi.list(params);
      setData(result);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, fetch };
}

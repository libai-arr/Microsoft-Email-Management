import { useEffect, useRef } from 'react';
import { tokensApi } from '@/services/api';
import type { TokenStatus } from '@/types';

export function useTokenStatus(
  ids: string[],
  onUpdate: (statuses: TokenStatus[]) => void,
  interval = 30000,
) {
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (ids.length === 0) return;

    const poll = async () => {
      try {
        const statuses = await tokensApi.status(ids);
        onUpdate(statuses);
      } catch {
        // silent — poll will retry
      }
    };

    poll();
    timerRef.current = setInterval(poll, interval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [ids.join(','), interval]);
}

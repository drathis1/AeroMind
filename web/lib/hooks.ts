"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface PollState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
}

/**
 * Poll an async fetcher on an interval. Ignores stale responses (if a newer
 * request started before an older one resolved).
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  deps: ReadonlyArray<unknown> = [],
): PollState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const seqRef = useRef(0);
  const mountedRef = useRef(true);

  const run = useCallback(async () => {
    const mySeq = ++seqRef.current;
    try {
      const result = await fetcher();
      if (!mountedRef.current || mySeq !== seqRef.current) return;
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      if (!mountedRef.current || mySeq !== seqRef.current) return;
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      if (mountedRef.current && mySeq === seqRef.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    void run();
    const id = setInterval(() => {
      void run();
    }, intervalMs);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [run, intervalMs]);

  return { data, error, loading, lastUpdated, refresh: run };
}

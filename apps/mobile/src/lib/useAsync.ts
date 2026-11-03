/* eslint-disable react-hooks/use-memo -- caller-supplied dependency list is intentional */
import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Last-request-wins fetch hook. Switching hotels/tabs must never let a stale
 * response from a previous API instance overwrite the currently selected hotel.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(false);
  const generation = useRef(0);
  const run = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const result = await fn();
      if (mounted.current && request === generation.current) setData(result);
    } catch (e) {
      if (mounted.current && request === generation.current) {
        setError(e instanceof Error ? e : new Error(String(e)));
      }
    } finally {
      if (mounted.current && request === generation.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mounted.current = true;
    void run();
    return () => { mounted.current = false; generation.current++; };
  }, [run]);

  return { data, error, loading, reload: run, setData };
}

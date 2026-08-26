import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

type AsyncState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (updater: T | ((current: T) => T)) => void;
};

/**
 * Loads data on mount and whenever `deps` change, with a `reload` escape hatch.
 * `setData` lets a screen apply an optimistic update without a round trip.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loaderRef
      .current()
      .then((result) => {
        if (!cancelled) setDataState(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // A 401 is handled globally by signing the user out; no error banner needed.
        if (err instanceof ApiError && err.status === 401) return;
        setError(err instanceof Error ? err.message : "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const setData = useCallback((updater: T | ((current: T) => T)) => {
    setDataState((current) =>
      typeof updater === "function"
        ? current === null
          ? current
          : (updater as (c: T) => T)(current)
        : updater,
    );
  }, []);

  return { data, error, loading, reload, setData };
}

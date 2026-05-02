import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * useApi — zero-latency perception hook.
 * 
 * Provides immediate shimmer state while data loads,
 * supports optimistic updates, and auto-refetches on key change.
 * 
 * Usage:
 *   const { data, loading, error, refetch } = useApi(listPatients);
 *   const { data, execute } = useApi(createPatient, { immediate: false });
 */
export function useApi(apiFunction, options = {}) {
    const { immediate = true, args = [], key = '' } = options;
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(immediate);
    const [error, setError] = useState(null);
    const mountedRef = useRef(true);

    const execute = useCallback(async (...executeArgs) => {
        setLoading(true);
        setError(null);

        const finalArgs = executeArgs.length > 0 ? executeArgs : args;
        const result = await apiFunction(...finalArgs);

        if (!mountedRef.current) return result;

        if (result.error) {
            setError(result.error);
            setData(null);
        } else {
            setData(result.data);
        }
        setLoading(false);
        return result;
    }, [apiFunction, ...args]);

    useEffect(() => {
        mountedRef.current = true;
        if (immediate) execute();
        return () => { mountedRef.current = false; };
    }, [key]);

    return { data, loading, error, execute, setData };
}

/**
 * C1PageShell — consistent page chrome for every C1 consumer page.
 *
 * Conventions (from the principal-engineer architecture brief):
 *  - One H1 with subtitle in muted text.
 *  - Primary action bar pinned above the fold.
 *  - Loading state uses PageSkeleton, not a spinner over a blank screen.
 *  - Error state uses an inline alert with retry, never a toast.
 *
 * Use this on every consumer-view page so the rhythm is identical.
 */

import { useEffect, useState, useCallback } from 'react';
import PrimaryActionBar from './PrimaryActionBar';
import PageSkeleton from './PageSkeleton';
import { AlertTriangle, RotateCw } from 'lucide-react';

export default function C1PageShell({
    title,
    subtitle,
    primaryAction,
    onPrimary,
    isLoading,
    error,
    onRetry,
    children,
    skeletonCardCount = 3,
}) {
    return (
        <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
            <header>
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100">
                    {title}
                </h1>
                {subtitle ? (
                    <p className="mt-1 text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-2xl">
                        {subtitle}
                    </p>
                ) : null}
            </header>

            {primaryAction ? (
                <PrimaryActionBar action={primaryAction} onClick={onPrimary} />
            ) : null}

            <section className="mt-2">
                {isLoading ? (
                    <PageSkeleton cardCount={skeletonCardCount} />
                ) : error ? (
                    <div
                        role="alert"
                        className="rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/30 p-4 sm:p-6"
                    >
                        <div className="flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 mt-0.5 text-rose-700 dark:text-rose-300 shrink-0" aria-hidden="true" />
                            <div className="min-w-0">
                                <p className="font-medium text-rose-800 dark:text-rose-200">
                                    Couldn&rsquo;t load this page
                                </p>
                                <p className="mt-1 text-sm text-rose-700/80 dark:text-rose-300/80 break-words">
                                    {String(error)}
                                </p>
                                {onRetry ? (
                                    <button
                                        type="button"
                                        onClick={onRetry}
                                        className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-rose-300 dark:border-rose-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm font-medium text-rose-700 dark:text-rose-200 hover:bg-rose-100 dark:hover:bg-rose-900/40"
                                    >
                                        <RotateCw aria-hidden="true" className="w-3.5 h-3.5" />
                                        Try again
                                    </button>
                                ) : null}
                            </div>
                        </div>
                    </div>
                ) : (
                    children
                )}
            </section>
        </main>
    );
}

/**
 * useBundleFetch — small data hook used by every page. Calls the
 * supplied bundle fn once, exposes { data, error, isLoading, retry }.
 */
export function useBundleFetch(fetchFn, deps = []) {
    const [state, setState] = useState({ data: null, error: null, isLoading: true });

    const run = useCallback(async () => {
        setState((s) => ({ ...s, isLoading: true, error: null }));
        const { data, error } = await fetchFn();
        setState({ data, error, isLoading: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    useEffect(() => { run(); }, [run]);
    return { ...state, retry: run };
}

import { useCallback, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    createJournalEntry,
    analyzeJournalText,
    getJournalEntries,
    getJournalTrends,
    rateJournalReframe,
    getDistortionCatalog,
} from '../api/client';


/**
 * Hook for the CBT Thought Journal — entries, analysis, trends.
 */
export function useJournal(userId) {
    const queryClient = useQueryClient();

    // ── Entries (last N days) ───────────────────────────────
    const {
        data: entries = [],
        isLoading: entriesLoading,
        refetch: refetchEntries,
    } = useQuery({
        queryKey: ['journalEntries', userId],
        queryFn: async () => {
            if (!userId) return [];
            const { data, error } = await getJournalEntries(userId, 30);
            if (error) throw new Error(error);
            return data || [];
        },
        enabled: !!userId,
        staleTime: 2 * 60 * 1000, // 2 min
    });

    // ── Trends ──────────────────────────────────────────────
    const {
        data: trends = null,
        isLoading: trendsLoading,
        refetch: refetchTrends,
    } = useQuery({
        queryKey: ['journalTrends', userId],
        queryFn: async () => {
            if (!userId) return null;
            const { data, error } = await getJournalTrends(userId, 30);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        staleTime: 5 * 60 * 1000, // 5 min
    });

    // ── Distortion Catalog ──────────────────────────────────
    const {
        data: catalog = null,
    } = useQuery({
        queryKey: ['distortionCatalog'],
        queryFn: async () => {
            const { data, error } = await getDistortionCatalog();
            if (error) throw new Error(error);
            return data;
        },
        staleTime: 60 * 60 * 1000, // 1 hour — catalog rarely changes
    });

    // ── Create Entry Mutation ───────────────────────────────
    const createMutation = useMutation({
        mutationFn: ({ text, date }) => createJournalEntry(userId, text, date),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['journalEntries', userId] });
            queryClient.invalidateQueries({ queryKey: ['journalTrends', userId] });
        },
    });

    // ── Rate Reframe Mutation ───────────────────────────────
    const rateMutation = useMutation({
        mutationFn: ({ entryId, helpful }) => rateJournalReframe(userId, entryId, helpful),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['journalEntries', userId] });
        },
    });

    // ── Actions ─────────────────────────────────────────────
    const submitEntry = useCallback(async (text, date = null) => {
        const { data, error } = await createMutation.mutateAsync({ text, date });
        return { data, error };
    }, [createMutation]);

    const rateReframe = useCallback(async (entryId, helpful) => {
        const { data, error } = await rateMutation.mutateAsync({ entryId, helpful });
        return { data, error };
    }, [rateMutation]);

    return {
        // Data
        entries,
        trends,
        catalog,

        // Loading
        entriesLoading,
        trendsLoading,

        // Actions
        submitEntry,
        rateReframe,
        refetchEntries,
        refetchTrends,

        // Action states
        isSubmitting: createMutation.isPending,
        submitError: createMutation.error?.message || null,
        isRating: rateMutation.isPending,
    };
}


/**
 * Hook for live distortion analysis while typing.
 * Debounced — only calls API when user pauses typing.
 */
export function useJournalAnalysis(userId) {
    const [analysis, setAnalysis] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const analyze = useCallback(async (text) => {
        if (!userId || !text || text.trim().length < 10) {
            setAnalysis(null);
            return;
        }
        setIsAnalyzing(true);
        try {
            const { data, error } = await analyzeJournalText(userId, text);
            if (!error && data) {
                setAnalysis(data);
            }
        } catch (e) {
            // Silently fail — live preview is optional
        } finally {
            setIsAnalyzing(false);
        }
    }, [userId]);

    const clearAnalysis = useCallback(() => {
        setAnalysis(null);
    }, []);

    return {
        analysis,
        isAnalyzing,
        analyze,
        clearAnalysis,
    };
}

export default useJournal;

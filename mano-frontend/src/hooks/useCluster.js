import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import clusterService from '../services/clusterService';
import { useNotification } from '../contexts/NotificationContext';

// Query keys
const CLUSTER_KEYS = {
    current: ['cluster', 'current'],
    peers: ['cluster', 'peers'],
    activities: ['cluster', 'activities'],
    transitions: ['cluster', 'transitions'],
    statistics: ['cluster', 'statistics'],
};

/**
 * Hook for current cluster
 */
export function useCurrentCluster() {
    return useQuery({
        queryKey: CLUSTER_KEYS.current,
        queryFn: () => clusterService.getCurrentCluster(),
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}

/**
 * Hook for peer group
 */
export function usePeers(limit = 10) {
    return useQuery({
        queryKey: [...CLUSTER_KEYS.peers, limit],
        queryFn: () => clusterService.getPeers(limit),
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook for recommended activities
 */
export function useActivities() {
    return useQuery({
        queryKey: CLUSTER_KEYS.activities,
        queryFn: () => clusterService.getActivities(),
        staleTime: 10 * 60 * 1000, // 10 minutes
    });
}

/**
 * Hook for cluster transitions
 */
export function useClusterTransitions() {
    return useQuery({
        queryKey: CLUSTER_KEYS.transitions,
        queryFn: () => clusterService.getTransitions(),
        staleTime: 10 * 60 * 1000,
    });
}

/**
 * Hook for cluster statistics (admin/professional)
 */
export function useClusterStatistics() {
    return useQuery({
        queryKey: CLUSTER_KEYS.statistics,
        queryFn: () => clusterService.getStatistics(),
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook for cluster assignment
 */
export function useAssignCluster() {
    const queryClient = useQueryClient();
    const { success, info, error } = useNotification();

    return useMutation({
        mutationFn: (scores) => clusterService.assignToCluster(scores),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: CLUSTER_KEYS.current });
            queryClient.invalidateQueries({ queryKey: CLUSTER_KEYS.peers });
            queryClient.invalidateQueries({ queryKey: CLUSTER_KEYS.activities });

            if (data.isTransition) {
                info(`Your peer group has changed to ${data.clusterName}`);
            } else {
                success('Cluster assignment updated');
            }
        },
        onError: (err) => {
            error(err.message || 'Failed to update cluster assignment');
        },
    });
}

/**
 * Hook for previewing cluster assignment
 */
export function usePreviewCluster() {
    return useMutation({
        mutationFn: (scores) => clusterService.previewAssignment(scores),
    });
}

export default {
    useCurrentCluster,
    usePeers,
    useActivities,
    useClusterTransitions,
    useClusterStatistics,
    useAssignCluster,
    usePreviewCluster,
};
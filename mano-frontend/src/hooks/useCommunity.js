import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import communityService from '../services/communityService';
import { getUserCommunity, getCommunityFeed, getCommunityUsers } from '../api/client';

// Map community_name → emoji icon
const COMMUNITY_ICON_MAP = {
    Thriving: '🌟',
    Stable: '💪',
    Growing: '🌱',
    Healing: '🤝',
    Supported: '❤️',
};

export function useCommunity(userId) {
    const queryClient = useQueryClient();

    // Get user's community from real API when userId available
    const {
        data: myCluster,
        isLoading: clusterLoading,
    } = useQuery({
        queryKey: ['myCluster', userId],
        queryFn: async () => {
            if (!userId) return null;
            const { data, error } = await getUserCommunity(userId);
            if (error || !data) return null;
            // Normalize to expected shape: { cluster: { id, name, description, icon } }
            return {
                cluster: {
                    id: data.id,
                    name: data.community_name,
                    description: data.description,
                    icon: COMMUNITY_ICON_MAP[data.community_name] || '👥',
                    characteristics: [],
                },
            };
        },
        enabled: !!userId,
    });

    // Get all clusters
    const {
        data: clusters = [],
        isLoading: clustersLoading,
    } = useQuery({
        queryKey: ['clusters'],
        queryFn: communityService.getClusters,
    });

    // Get peers
    const {
        data: peers = [],
        isLoading: peersLoading,
        refetch: refetchPeers,
    } = useQuery({
        queryKey: ['peers'],
        queryFn: () => communityService.getPeers(),
    });

    // Get community members
    const communityId = myCluster?.cluster?.id;
    const {
        data: membersData,
        isLoading: membersLoading,
    } = useQuery({
        queryKey: ['communityMembers', communityId],
        queryFn: async () => {
            if (!communityId) return [];
            const { data, error } = await getCommunityUsers(communityId);
            if (error) throw new Error(error);
            return (data || []).map((m) => ({
                id: m.user_id,
                name: m.guest_name,
                firstName: m.guest_name,
                lastName: '',
                avatar: null,
                status: 'online',
            }));
        },
        enabled: !!communityId,
    });

    // Get community feed — server resolves community from userId directly
    const {
        data: feedData,
        isLoading: feedLoading,
        refetch: refetchFeed,
    } = useQuery({
        queryKey: ['communityFeed', userId],
        queryFn: async () => {
            if (!userId) return [];
            const { data, error } = await getCommunityFeed(userId);
            if (error) throw new Error(error);
            return (data || []).map((p) => {
                // Normalize API shape → CommunityPost component shape
                const nameParts = (p.author_name || `User ${p.author_id}`).split(' ');
                return {
                    id: p.id,
                    type: p.post_type,
                    content: p.paragraph,
                    timestamp: p.created_at,
                    likes: p.likes ?? 0,
                    comments: p.comments ?? 0,
                    isLiked: false,
                    author: {
                        id: p.author_id,
                        firstName: nameParts[0] || '',
                        lastName: nameParts.slice(1).join(' ') || '',
                        avatar: null,
                        status: 'online',
                    },
                };
            });
        },
        enabled: !!userId,
    });

    // Connect with peer
    const connectMutation = useMutation({
        mutationFn: communityService.connectPeer,
        onSuccess: () => {
            queryClient.invalidateQueries(['peers']);
        },
    });

    // Disconnect from peer
    const disconnectMutation = useMutation({
        mutationFn: communityService.disconnectPeer,
        onSuccess: () => {
            queryClient.invalidateQueries(['peers']);
        },
    });

    // Create post
    const createPostMutation = useMutation({
        mutationFn: ({ communityId, userId, content, type }) =>
            communityService.createPost(communityId, userId, content, type),
        onSuccess: () => {
            queryClient.invalidateQueries(['communityFeed', userId]);
        },
    });

    // Toggle like
    const toggleLikeMutation = useMutation({
        mutationFn: communityService.toggleLike,
        onSuccess: () => {
            queryClient.invalidateQueries(['communityFeed', userId]);
        },
    });

    // Helper functions
    const connectPeer = useCallback((peerId) => {
        return connectMutation.mutateAsync(peerId);
    }, [connectMutation]);

    const disconnectPeer = useCallback((peerId) => {
        return disconnectMutation.mutateAsync(peerId);
    }, [disconnectMutation]);

    const createPost = useCallback((content, type) => {
        const communityId = myCluster?.cluster?.id;
        return createPostMutation.mutateAsync({ communityId, userId, content, type });
    }, [createPostMutation, myCluster, userId]);

    const toggleLike = useCallback((postId) => {
        return toggleLikeMutation.mutateAsync(postId);
    }, [toggleLikeMutation]);

    // Computed values
    const connectedPeers = peers.filter((p) => p.isConnected);
    // Use actual community members for "Online Now"
    const onlinePeers = (membersData || []).filter((p) => p.status === 'online');

    return {
        // Data
        myCluster,
        clusters,
        peers,
        connectedPeers,
        onlinePeers,
        feed: Array.isArray(feedData) ? feedData : (feedData?.content || []),
        members: membersData || [],

        // Loading states
        isLoading: clusterLoading || peersLoading,
        clusterLoading,
        peersLoading,
        feedLoading,
        membersLoading,

        // Actions
        connectPeer,
        disconnectPeer,
        createPost,
        toggleLike,
        refetchPeers,
        refetchFeed,

        // Action states
        isConnecting: connectMutation.isPending,
        isCreatingPost: createPostMutation.isPending,
    };
}

export function usePeerMessages(peerId) {
    const queryClient = useQueryClient();

    const {
        data: messages = [],
        isLoading,
        refetch,
    } = useQuery({
        queryKey: ['peerMessages', peerId],
        queryFn: () => communityService.getMessages(peerId),
        enabled: !!peerId,
    });

    const sendMutation = useMutation({
        mutationFn: ({ peerId, content }) => communityService.sendMessage(peerId, content),
        onSuccess: () => {
            queryClient.invalidateQueries(['peerMessages', peerId]);
        },
    });

    const sendMessage = useCallback((content) => {
        return sendMutation.mutateAsync({ peerId, content });
    }, [peerId, sendMutation]);

    return {
        messages,
        isLoading,
        sendMessage,
        isSending: sendMutation.isPending,
        refetch,
    };
}

export function usePeerProfile(peerId) {
    return useQuery({
        queryKey: ['peer', peerId],
        queryFn: () => communityService.getPeer(peerId),
        enabled: !!peerId,
    });
}

export default useCommunity;
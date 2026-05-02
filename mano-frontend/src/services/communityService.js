import api from './api';
import { createCommunityPost, getCommunityClusters } from '../api/client';

// Mock delay
const mockDelay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock cluster data
const mockClusters = {
    0: {
        id: 0,
        name: 'Thriving',
        description: 'Members who are doing well and maintaining positive mental health',
        icon: '🌟',
        color: 'success',
        memberCount: 1247,
        characteristics: ['High resilience', 'Strong coping skills', 'Positive outlook'],
    },
    1: {
        id: 1,
        name: 'Stable',
        description: 'Members maintaining balance with occasional challenges',
        icon: '💪',
        color: 'primary',
        memberCount: 2893,
        characteristics: ['Consistent mood', 'Good self-awareness', 'Regular self-care'],
    },
    2: {
        id: 2,
        name: 'Growing',
        description: 'Members actively working on improving their mental wellness',
        icon: '🌱',
        color: 'warning',
        memberCount: 1856,
        characteristics: ['Open to change', 'Seeking support', 'Building habits'],
    },
    3: {
        id: 3,
        name: 'Healing',
        description: 'Members recovering and rebuilding their mental health',
        icon: '🤝',
        color: 'accent',
        memberCount: 934,
        characteristics: ['In recovery', 'Building resilience', 'Seeking connection'],
    },
    4: {
        id: 4,
        name: 'Supported',
        description: 'Members receiving enhanced support during difficult times',
        icon: '❤️',
        color: 'danger',
        memberCount: 412,
        characteristics: ['Needs support', 'Professional guidance', 'Community care'],
    },
};

// Mock peers data
const mockPeers = [
    {
        id: 'peer-1',
        firstName: 'Sarah',
        lastName: 'M',
        avatar: null,
        clusterId: 1,
        clusterName: 'Stable',
        status: 'online',
        bio: 'Finding peace in daily mindfulness practices 🧘',
        joinedDate: '2024-06-15',
        interests: ['Meditation', 'Journaling', 'Nature walks'],
        commonInterests: ['Meditation', 'Journaling'],
        isConnected: true,
        lastActive: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    },
    {
        id: 'peer-2',
        firstName: 'Michael',
        lastName: 'K',
        avatar: null,
        clusterId: 1,
        clusterName: 'Stable',
        status: 'online',
        bio: 'Working on anxiety management, one day at a time',
        joinedDate: '2024-08-22',
        interests: ['Exercise', 'Reading', 'Music'],
        commonInterests: ['Exercise'],
        isConnected: true,
        lastActive: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    },
    {
        id: 'peer-3',
        firstName: 'Emily',
        lastName: 'R',
        avatar: null,
        clusterId: 1,
        clusterName: 'Stable',
        status: 'away',
        bio: 'Believer in the power of small steps',
        joinedDate: '2024-09-01',
        interests: ['Art therapy', 'Cooking', 'Meditation'],
        commonInterests: ['Meditation'],
        isConnected: false,
        lastActive: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'peer-4',
        firstName: 'James',
        lastName: 'T',
        avatar: null,
        clusterId: 1,
        clusterName: 'Stable',
        status: 'offline',
        bio: 'Learning to prioritize mental health',
        joinedDate: '2024-07-10',
        interests: ['Running', 'Podcasts', 'Gardening'],
        commonInterests: [],
        isConnected: false,
        lastActive: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'peer-5',
        firstName: 'Lisa',
        lastName: 'W',
        avatar: null,
        clusterId: 1,
        clusterName: 'Stable',
        status: 'online',
        bio: 'Grateful for this supportive community 💙',
        joinedDate: '2024-05-20',
        interests: ['Yoga', 'Writing', 'Volunteering'],
        commonInterests: ['Writing'],
        isConnected: true,
        lastActive: new Date().toISOString(),
    },
];

// Mock community posts/activity
const mockPosts = [
    {
        id: 'post-1',
        author: mockPeers[0],
        content: "Just completed my 30-day meditation streak! 🎉 It's amazing how much more centered I feel. Anyone else working on building consistent habits?",
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        likes: 24,
        comments: 8,
        isLiked: false,
        type: 'milestone',
    },
    {
        id: 'post-2',
        author: mockPeers[1],
        content: "Had a tough day but reminded myself that it's okay to not be okay. Tomorrow is a new day. 🌅",
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        likes: 42,
        comments: 15,
        isLiked: true,
        type: 'reflection',
    },
    {
        id: 'post-3',
        author: mockPeers[4],
        content: "Tip that helped me today: When feeling overwhelmed, I step outside for 5 minutes and focus on what I can see, hear, and feel. Simple but effective grounding technique!",
        timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
        likes: 67,
        comments: 12,
        isLiked: false,
        type: 'tip',
    },
    {
        id: 'post-4',
        author: mockPeers[2],
        content: "Looking for accountability partners for a weekly check-in. Anyone interested in starting a small support group?",
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        likes: 31,
        comments: 23,
        isLiked: false,
        type: 'discussion',
    },
];

// Mock messages
let mockMessages = {
    'peer-1': [
        {
            id: 'msg-1',
            senderId: 'peer-1',
            content: 'Hey! I noticed we both like meditation. Have you tried any guided sessions?',
            timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            read: true,
        },
        {
            id: 'msg-2',
            senderId: 'user',
            content: "Hi Sarah! Yes, I've been using some apps. Do you have any recommendations?",
            timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 3600000).toISOString(),
            read: true,
        },
        {
            id: 'msg-3',
            senderId: 'peer-1',
            content: "I really like the ones focused on breathing. They help me when I'm feeling anxious.",
            timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            read: true,
        },
    ],
    'peer-2': [
        {
            id: 'msg-4',
            senderId: 'peer-2',
            content: 'Thanks for the support in my post yesterday!',
            timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
            read: false,
        },
    ],
};

const communityService = {
    // Get user's cluster info
    getMyCluster: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return {
                cluster: mockClusters[1],
                assignedAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
                confidence: 0.87,
            };
        }
        const response = await api.get('/community/my-cluster');
        return response.data;
    },

    // Get all clusters info
    getClusters: async () => {
        let backendCounts = [];
        try {
            const { data, error } = await getCommunityClusters();
            if (!error && data) {
                backendCounts = data;
            }
        } catch (err) {
            console.error('Failed to fetch cluster counts:', err);
        }

        // Merge backend counts into mock clusters metadata for UI presentation
        return Object.values(mockClusters).map((cluster) => {
            const backendCluster = backendCounts.find(
                (c) => c.name.toLowerCase() === cluster.name.toLowerCase()
            );
            return {
                ...cluster,
                memberCount: backendCluster ? backendCluster.memberCount : 0,
            };
        });
    },

    // Get peers in user's cluster
    getPeers: async (options = {}) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            let peers = [...mockPeers];

            if (options.onlineOnly) {
                peers = peers.filter((p) => p.status === 'online');
            }
            if (options.connectedOnly) {
                peers = peers.filter((p) => p.isConnected);
            }

            return peers;
        }
        const response = await api.get('/community/peers', { params: options });
        return response.data;
    },

    // Get single peer profile
    getPeer: async (peerId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return mockPeers.find((p) => p.id === peerId);
        }
        const response = await api.get(`/community/peers/${peerId}`);
        return response.data;
    },

    // Connect with a peer
    connectPeer: async (peerId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            const peer = mockPeers.find((p) => p.id === peerId);
            if (peer) {
                peer.isConnected = true;
            }
            return { success: true };
        }
        const response = await api.post(`/community/peers/${peerId}/connect`);
        return response.data;
    },

    // Disconnect from a peer
    disconnectPeer: async (peerId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            const peer = mockPeers.find((p) => p.id === peerId);
            if (peer) {
                peer.isConnected = false;
            }
            return { success: true };
        }
        const response = await api.delete(`/community/peers/${peerId}/connect`);
        return response.data;
    },

    // Get community feed
    getFeed: async (page = 0, size = 10) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return {
                content: mockPosts,
                totalElements: mockPosts.length,
                totalPages: 1,
                number: page,
            };
        }
        const response = await api.get('/community/feed', { params: { page, size } });
        return response.data;
    },

    // Create a post
    createPost: async (communityId, userId, content, type = 'reflect') => {
        const { data, error } = await createCommunityPost(communityId, userId, {
            post_type: type,
            paragraph: content,
        });
        if (error) throw new Error(error);
        return data;
    },

    // Like/unlike a post
    toggleLike: async (postId) => {
        if (import.meta.env.DEV) {
            await mockDelay(200);
            const post = mockPosts.find((p) => p.id === postId);
            if (post) {
                post.isLiked = !post.isLiked;
                post.likes += post.isLiked ? 1 : -1;
            }
            return { success: true, isLiked: post?.isLiked };
        }
        const response = await api.post(`/community/posts/${postId}/like`);
        return response.data;
    },

    // Get messages with a peer
    getMessages: async (peerId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return mockMessages[peerId] || [];
        }
        const response = await api.get(`/community/messages/${peerId}`);
        return response.data;
    },

    // Send message to a peer
    sendMessage: async (peerId, content) => {
        if (import.meta.env.DEV) {
            await mockDelay(300);
            const newMessage = {
                id: `msg-${Date.now()}`,
                senderId: 'user',
                content,
                timestamp: new Date().toISOString(),
                read: true,
            };

            if (!mockMessages[peerId]) {
                mockMessages[peerId] = [];
            }
            mockMessages[peerId].push(newMessage);

            return newMessage;
        }
        const response = await api.post(`/community/messages/${peerId}`, { content });
        return response.data;
    },

    // Get unread message count
    getUnreadCount: async () => {
        if (import.meta.env.DEV) {
            await mockDelay(200);
            let count = 0;
            Object.values(mockMessages).forEach((msgs) => {
                count += msgs.filter((m) => !m.read && m.senderId !== 'user').length;
            });
            return { count };
        }
        const response = await api.get('/community/messages/unread-count');
        return response.data;
    },

    // Get community guidelines
    getGuidelines: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return {
                guidelines: [
                    {
                        title: 'Be Kind and Supportive',
                        description: 'Treat everyone with respect and empathy. We\'re all on our own journey.',
                    },
                    {
                        title: 'Protect Privacy',
                        description: 'Don\'t share personal information about yourself or others outside the community.',
                    },
                    {
                        title: 'No Medical Advice',
                        description: 'Share experiences, not diagnoses. Professional help should come from professionals.',
                    },
                    {
                        title: 'Report Concerns',
                        description: 'If you see something concerning, report it to help keep our community safe.',
                    },
                    {
                        title: 'Stay Positive',
                        description: 'Focus on growth and support. Negativity and judgment have no place here.',
                    },
                ],
            };
        }
        const response = await api.get('/community/guidelines');
        return response.data;
    },
};

export default communityService;
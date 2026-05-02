import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Button, Tabs, Badge, EmptyState, Alert } from '../../components/common';
import {
    ClusterCard,
    ClusterBadge,
    CommunityPost,
    CreatePostModal,
    PeerMessageModal,
    PeerList,
    CommunityGuidelines,
    PeerCard,
    MoodCheckIn,
    StreakBadges,
    WeeklyWellnessSummary,
} from '../../components/features/community';
import { CrisisSafetyBanner } from '../../components/features/crisis';
import { useCommunity } from '../../hooks/useCommunity';
import { useAuth } from '../../contexts/AuthContext';
import {
    PlusIcon,
    UserGroupIcon,
    ChatBubbleLeftRightIcon,
    SparklesIcon,
    InformationCircleIcon,
    ShieldCheckIcon,
} from '@heroicons/react/24/outline';

function Community() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [showCreatePost, setShowCreatePost] = useState(false);
    const [showGuidelines, setShowGuidelines] = useState(false);
    const [selectedPeer, setSelectedPeer] = useState(null);
    const [showPeerMessage, setShowPeerMessage] = useState(false);

    const {
        myCluster,
        clusters,
        peers,
        connectedPeers,
        onlinePeers,
        feed,
        members,
        isLoading,
        feedLoading,
        membersLoading,
        connectPeer,
        createPost,
        toggleLike,
        isCreatingPost,
    } = useCommunity(user?.id);

    const handleMessage = (peer) => {
        setSelectedPeer(peer);
        setShowPeerMessage(true);
    };

    const handleConnect = async (peer) => {
        await connectPeer(peer.id);
    };

    const handleCreatePost = async (content, type) => {
        await createPost(content, type);
    };

    const handleLike = async (postId) => {
        await toggleLike(postId);
    };

    const handleViewProfile = (peer) => {
        // Could navigate to a peer profile page
        console.log('View profile:', peer);
    };

    const tabs = [
        {
            id: 'feed',
            label: 'Feed',
            icon: <SparklesIcon className="w-4 h-4" />,
            badge: feed.length > 0 ? feed.length : undefined,
            content: (
                <div className="space-y-4">
                    {/* Mood Check-In */}
                    <MoodCheckIn userId={user?.id} />

                    {/* Create Post Button */}
                    <Card className="p-4">
                        <button
                            onClick={() => setShowCreatePost(true)}
                            className="w-full flex items-center gap-3 p-3 bg-cream/50 rounded-2xl text-neutral-500 hover:bg-cream transition-colors text-left"
                        >
                            <div className="w-10 h-10 rounded-full bg-peach/40 flex items-center justify-center">
                                <PlusIcon className="w-5 h-5 text-terracotta" />
                            </div>
                            <span>Share something with your community...</span>
                        </button>
                    </Card>

                    {/* Feed */}
                    {feedLoading ? (
                        <div className="space-y-4">
                            {[1, 2, 3].map((i) => (
                                <Card key={i} className="animate-pulse">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-12 h-12 bg-sand/40 rounded-full" />
                                        <div className="flex-1">
                                            <div className="h-4 bg-sand/40 rounded w-1/4 mb-2" />
                                            <div className="h-3 bg-sand/40 rounded w-1/3" />
                                        </div>
                                    </div>
                                    <div className="h-20 bg-sand/40 rounded-2xl" />
                                </Card>
                            ))}
                        </div>
                    ) : feed.length === 0 ? (
                        <Card>
                            <EmptyState
                                icon={<SparklesIcon className="w-8 h-8" />}
                                title="No posts yet"
                                description="Be the first to share something with your community!"
                                actionLabel="Create Post"
                                onAction={() => setShowCreatePost(true)}
                            />
                        </Card>
                    ) : (
                        <div className="space-y-4">
                            {feed.map((post) => (
                                <CommunityPost
                                    key={post.id}
                                    post={post}
                                    onLike={handleLike}
                                    onComment={(id) => console.log('Comment on:', id)}
                                    onShare={(id) => console.log('Share:', id)}
                                    onAuthorClick={(author) => handleViewProfile(author)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            ),
        },
        {
            id: 'members',
            label: 'Members',
            icon: <UserGroupIcon className="w-4 h-4" />,
            badge: members.length > 0 ? members.length : undefined,
            content: (
                <div className="space-y-3">
                    {membersLoading ? (
                        <Card>
                            <div className="space-y-3">
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="flex items-center gap-3 animate-pulse">
                                        <div className="w-10 h-10 rounded-full bg-sand/40" />
                                        <div className="flex-1">
                                            <div className="h-3 bg-sand/40 rounded w-1/3" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </Card>
                    ) : members.length === 0 ? (
                        <Card>
                            <EmptyState
                                icon={<UserGroupIcon className="w-8 h-8" />}
                                title="No members yet"
                                description="Be the first to join this community!"
                            />
                        </Card>
                    ) : (
                        <Card>
                            <CardHeader>
                                <CardTitle>{members.length} Member{members.length !== 1 ? 's' : ''}</CardTitle>
                            </CardHeader>
                            <div className="space-y-2">
                                {members.map((member) => (
                                    <div key={member.id} className="flex items-center gap-3 p-2 rounded-2xl hover:bg-cream/50 transition-colors">
                                        <div className="w-10 h-10 rounded-full bg-peach/50 flex items-center justify-center text-terracotta-dark font-semibold text-sm flex-shrink-0">
                                            {member.name?.[0]?.toUpperCase() || '?'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-neutral-900 truncate">{member.name}</p>
                                            <p className="text-xs text-neutral-500">Community member</p>
                                        </div>
                                        {member.id === user?.id && (
                                            <span className="text-xs text-terracotta bg-cream px-2 py-0.5 rounded-full font-medium">You</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </Card>
                    )}
                </div>
            ),
        },
        {
            id: 'connections',
            label: 'Connections',
            icon: <ChatBubbleLeftRightIcon className="w-4 h-4" />,
            badge: connectedPeers.length > 0 ? connectedPeers.length : undefined,
            content: (
                <div className="space-y-6">
                    {connectedPeers.length === 0 ? (
                        <Card>
                            <EmptyState
                                icon={<ChatBubbleLeftRightIcon className="w-8 h-8" />}
                                title="No connections yet"
                                description="Connect with community members to start conversations"
                                actionLabel="Browse Members"
                            />
                        </Card>
                    ) : (
                        <Card>
                            <CardHeader>
                                <CardTitle>Your Connections</CardTitle>
                            </CardHeader>
                            <div className="space-y-3">
                                {connectedPeers.map((peer) => (
                                    <PeerCard
                                        key={peer.id}
                                        peer={peer}
                                        onMessage={handleMessage}
                                        isConnected={true}
                                    />
                                ))}
                            </div>
                        </Card>
                    )}
                </div>
            ),
        },
    ];

    return (
        <PageContainer
            title="Community"
            subtitle="Connect with others on similar journeys"
            actions={
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowGuidelines(true)}
                        leftIcon={<ShieldCheckIcon className="w-4 h-4" />}
                    >
                        Guidelines
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setShowCreatePost(true)}
                        leftIcon={<PlusIcon className="w-4 h-4" />}
                    >
                        Create Post
                    </Button>
                </div>
            }
        >
            {/* Cluster Info Banner */}
            {myCluster && (
                <div className="mb-6">
                    <ClusterCard
                        cluster={myCluster.cluster}
                        isUserCluster={true}
                    />
                </div>
            )}

            {/* Info Alert */}
            <Alert variant="info" className="mb-6">
                <div className="flex items-start gap-3">
                    <InformationCircleIcon className="w-5 h-5 text-terracotta flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="text-sm text-terracotta-dark">
                            You've been matched with the <strong>{myCluster?.cluster?.name}</strong> community
                            based on your assessment results. Members here share similar experiences and can
                            provide peer support.
                        </p>
                    </div>
                </div>
            </Alert>

            {/* Main Content with Tabs */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Column */}
                <div className="lg:col-span-2">
                    <Tabs tabs={tabs} defaultTab="feed" variant="pills" />
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Crisis Safety Banner */}
                    <CrisisSafetyBanner userId={user?.id} />

                    {/* Weekly Wellness Summary */}
                    <WeeklyWellnessSummary userId={user?.id} variant="compact" />

                    {/* Streaks & Badges */}
                    <StreakBadges userId={user?.id} variant="compact" />

                    {/* Online Now */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-sage animate-pulse" />
                                Online Now
                            </CardTitle>
                        </CardHeader>
                        {onlinePeers.length === 0 ? (
                            <p className="text-sm text-neutral-500 text-center py-4">
                                No members online right now
                            </p>
                        ) : (
                            <div className="space-y-2">
                                {onlinePeers.slice(0, 5).map((peer) => (
                                    <PeerCard
                                        key={peer.id}
                                        peer={peer}
                                        compact
                                        onMessage={handleMessage}
                                    />
                                ))}
                                {onlinePeers.length > 5 && (
                                    <p className="text-sm text-terracotta-light text-center pt-2">
                                        +{onlinePeers.length - 5} more online
                                    </p>
                                )}
                            </div>
                        )}
                    </Card>

                    {/* All Clusters Overview */}
                    <Card>
                        <CardHeader>
                            <CardTitle>All Communities</CardTitle>
                        </CardHeader>
                        <div className="space-y-2">
                            {clusters.map((cluster) => (
                                <ClusterCard
                                    key={cluster.id}
                                    cluster={cluster}
                                    compact
                                    isUserCluster={cluster.name === myCluster?.cluster?.name}
                                />
                            ))}
                        </div>
                    </Card>
                </div>
            </div>

            {/* Modals */}
            <CreatePostModal
                isOpen={showCreatePost}
                onClose={() => setShowCreatePost(false)}
                onSubmit={handleCreatePost}
                isSubmitting={isCreatingPost}
            />

            <PeerMessageModal
                isOpen={showPeerMessage}
                onClose={() => {
                    setShowPeerMessage(false);
                    setSelectedPeer(null);
                }}
                peer={selectedPeer}
            />

            <CommunityGuidelines
                isOpen={showGuidelines}
                onClose={() => setShowGuidelines(false)}
            />
        </PageContainer>
    );
}

export default Community;
import { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Button, Modal, Tabs, Badge } from '../../components/common';
import {
    ProfileHeader,
    ProfileForm,
    ProfileStats,
} from '../../components/features/profile';
import { ClusterBadge } from '../../components/features/community';
import { useProfile } from '../../hooks/useProfile';
import { useCommunity } from '../../hooks/useCommunity';
import { useAuth } from '../../contexts/AuthContext';
import {
    UserGroupIcon,
    ShieldCheckIcon,
} from '@heroicons/react/24/outline';

function Profile() {
    const [showEditModal, setShowEditModal] = useState(false);
    const { user } = useAuth();

    const {
        profile,
        isLoading,
        updateProfile,
        updateAvatar,
        deleteAvatar,
        isUpdating,
        isUploadingAvatar,
    } = useProfile();

    const { myCluster } = useCommunity(user?.id);

    // Build a profile object using the real guest_name from auth context,
    // keeping the rest of the (component1) profile data for stats etc.
    const guestName = user?.guest_name || user?.username || 'Guest';
    const realProfile = {
        ...(profile || {}),
        firstName: guestName,
        lastName: '',
        username: guestName,
        avatar: profile?.avatar ?? null,
    };

    const handleUpdateProfile = async (data) => {
        await updateProfile(data);
        setShowEditModal(false);
    };

    if (isLoading) {
        return (
            <PageContainer>
                <div className="animate-pulse">
                    <div className="h-40 bg-sand/30 rounded-t-3xl" />
                    <div className="px-6 pb-6 bg-white rounded-b-3xl">
                        <div className="-mt-16">
                            <div className="w-32 h-32 bg-sand/40 rounded-full" />
                        </div>
                        <div className="mt-4 space-y-3">
                            <div className="h-8 bg-sand/30 rounded-2xl w-1/3" />
                            <div className="h-4 bg-sand/30 rounded-2xl w-1/4" />
                            <div className="h-4 bg-sand/30 rounded-2xl w-1/2" />
                        </div>
                    </div>
                </div>
            </PageContainer>
        );
    }

    const tabs = [
        {
            id: 'overview',
            label: 'Overview',
            content: (
                <div className="grid gap-6 lg:grid-cols-2">
                    {/* About */}
                    <Card>
                        <CardHeader>
                            <CardTitle>About</CardTitle>
                        </CardHeader>
                        <div className="space-y-4">
                            <div className="flex items-start gap-3 p-3 bg-cream rounded-2xl border border-sand/40">
                                <ShieldCheckIcon className="w-5 h-5 text-sage mt-0.5 shrink-0" />
                                <div>
                                    <p className="text-sm font-medium text-sage-dark">Your data is protected</p>
                                    <p className="text-sm text-terracotta-light mt-0.5">
                                        We do not store or use your personal data. All insights and recommendations are generated entirely from synthetic data.
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-peach/50 flex items-center justify-center shrink-0">
                                    <span className="text-sm font-bold text-terracotta">
                                        {guestName.charAt(0).toUpperCase()}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-sm text-neutral-500">Guest Name</p>
                                    <p className="font-medium text-neutral-900">{guestName}</p>
                                </div>
                            </div>
                        </div>
                    </Card>

                    {/* Community */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <UserGroupIcon className="w-5 h-5 text-neutral-400" />
                                Community
                            </CardTitle>
                        </CardHeader>
                        {myCluster ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl">{myCluster.cluster?.icon}</span>
                                    <div>
                                        <p className="font-semibold text-neutral-900">{myCluster.cluster?.name}</p>
                                        <p className="text-sm text-neutral-500">{myCluster.cluster?.description}</p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {myCluster.cluster?.characteristics?.map((char, i) => (
                                        <Badge key={i} variant="secondary" size="sm">
                                            {char}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <p className="text-neutral-500">Complete an assessment to join a community</p>
                        )}
                    </Card>

                </div>
            ),
        },
        {
            id: 'progress',
            label: 'Progress',
            content: <ProfileStats stats={realProfile?.stats} />,
        },
    ];

    return (
        <PageContainer>
            {/* Profile Header */}
            <Card className="p-0 overflow-hidden mb-6">
                <ProfileHeader
                    profile={realProfile}
                    onEditProfile={() => setShowEditModal(true)}
                    onUpdateAvatar={updateAvatar}
                    onDeleteAvatar={deleteAvatar}
                    isUploadingAvatar={isUploadingAvatar}
                />
            </Card>

            {/* Tabs */}
            <Tabs tabs={tabs} defaultTab="overview" variant="pills" />

            {/* Edit Profile Modal */}
            <Modal
                isOpen={showEditModal}
                onClose={() => setShowEditModal(false)}
                title="Edit Profile"
                size="xl"
            >
                <ProfileForm
                    profile={realProfile}
                    onSubmit={handleUpdateProfile}
                    onCancel={() => setShowEditModal(false)}
                    isSubmitting={isUpdating}
                />
            </Modal>
        </PageContainer>
    );
}

export default Profile;
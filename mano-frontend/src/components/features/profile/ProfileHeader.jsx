import { useRef, useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Avatar, Button, Badge } from '../../common';
import {
    CameraIcon,
    PencilIcon,
    TrashIcon,
    CheckBadgeIcon,
} from '@heroicons/react/24/outline';

function ProfileHeader({
                           profile,
                           onEditProfile,
                           onUpdateAvatar,
                           onDeleteAvatar,
                           isUploadingAvatar = false,
                           editable = true,
                           className,
                       }) {
    const fileInputRef = useRef(null);
    const [showAvatarOptions, setShowAvatarOptions] = useState(false);

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            onUpdateAvatar?.(file);
        }
        setShowAvatarOptions(false);
    };

    const handleAvatarClick = () => {
        if (editable) {
            setShowAvatarOptions(!showAvatarOptions);
        }
    };

    return (
        <div className={cn('relative', className)}>
            {/* Banner */}
            <div className="h-32 sm:h-40 bg-gradient-to-r from-primary-500 to-primary-600 rounded-t-2xl" />

            {/* Profile Info */}
            <div className="px-4 sm:px-6 pb-6">
                <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between -mt-16 sm:-mt-20">
                    {/* Avatar */}
                    <div className="relative">
                        <div
                            onClick={handleAvatarClick}
                            className={cn(
                                'relative inline-block',
                                editable && 'cursor-pointer group'
                            )}
                        >
                            <Avatar
                                src={profile?.avatar}
                                firstName={profile?.firstName}
                                lastName={profile?.lastName}
                                size="2xl"
                                className="ring-4 ring-white"
                            />

                            {editable && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                                    <CameraIcon className="w-8 h-8 text-white" />
                                </div>
                            )}

                            {isUploadingAvatar && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-full">
                                    <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                </div>
                            )}
                        </div>

                        {/* Avatar Options Dropdown */}
                        {showAvatarOptions && (
                            <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-neutral-100 overflow-hidden z-10">
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left hover:bg-neutral-50 transition-colors"
                                >
                                    <CameraIcon className="w-5 h-5 text-neutral-500" />
                                    Upload Photo
                                </button>
                                {profile?.avatar && (
                                    <button
                                        onClick={() => {
                                            onDeleteAvatar?.();
                                            setShowAvatarOptions(false);
                                        }}
                                        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-left text-crisis-600 hover:bg-crisis-50 transition-colors"
                                    >
                                        <TrashIcon className="w-5 h-5" />
                                        Remove Photo
                                    </button>
                                )}
                            </div>
                        )}

                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleFileSelect}
                            className="hidden"
                        />
                    </div>

                    {/* Edit Button */}
                    {editable && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onEditProfile}
                            leftIcon={<PencilIcon className="w-4 h-4" />}
                            className="mt-4 sm:mt-0"
                        >
                            Edit Profile
                        </Button>
                    )}
                </div>

                {/* Name & Info */}
                <div className="mt-4">
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold text-neutral-900">
                            {profile?.firstName} {profile?.lastName}
                        </h1>
                        {profile?.emailVerified && (
                            <CheckBadgeIcon className="w-6 h-6 text-primary-500" />
                        )}
                    </div>
                    <p className="text-neutral-500">@{profile?.username}</p>

                    {profile?.bio && (
                        <p className="mt-3 text-neutral-600 max-w-2xl">{profile?.bio}</p>
                    )}

                    {/* Stats */}
                    <div className="flex flex-wrap gap-6 mt-4">
                        <div>
              <span className="text-2xl font-bold text-neutral-900">
                {profile?.stats?.daysActive || 0}
              </span>
                            <span className="text-neutral-500 ml-1">days active</span>
                        </div>
                        <div>
              <span className="text-2xl font-bold text-neutral-900">
                {profile?.stats?.currentStreak || 0}
              </span>
                            <span className="text-neutral-500 ml-1">day streak</span>
                        </div>
                        <div>
              <span className="text-2xl font-bold text-neutral-900">
                {profile?.stats?.activitiesCompleted || 0}
              </span>
                            <span className="text-neutral-500 ml-1">activities</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Click outside to close avatar options */}
            {showAvatarOptions && (
                <div
                    className="fixed inset-0 z-0"
                    onClick={() => setShowAvatarOptions(false)}
                />
            )}
        </div>
    );
}

export default ProfileHeader;
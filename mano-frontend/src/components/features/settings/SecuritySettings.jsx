import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { changePasswordSchema } from '../../../utils/validations';
import { cn } from '../../../utils/helpers';
import { Card, Button, Input, Modal, Alert } from '../../common';
import { PasswordStrength } from '../../common';
import { useSessions } from '../../../hooks/useProfile';
import { format, formatDistanceToNow } from 'date-fns';
import {
    KeyIcon,
    DevicePhoneMobileIcon,
    ComputerDesktopIcon,
    TrashIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import SettingsSection from './SettingsSection';

function SecuritySettings({
                              onChangePassword,
                              isChangingPassword = false,
                          }) {
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const { sessions, isLoading: sessionsLoading, revokeSession, isRevoking } = useSessions();

    const {
        register,
        handleSubmit,
        watch,
        reset,
        formState: { errors },
    } = useForm({
        resolver: yupResolver(changePasswordSchema),
    });

    const watchPassword = watch('newPassword');

    const handlePasswordSubmit = async (data) => {
        try {
            await onChangePassword(data.currentPassword, data.newPassword);
            setShowPasswordModal(false);
            reset();
        } catch (error) {
            // Error handled by hook
        }
    };

    const handleRevokeSession = async (sessionId) => {
        await revokeSession(sessionId);
    };

    return (
        <div className="space-y-6">
            {/* Password */}
            <SettingsSection
                title="Password"
                description="Keep your account secure with a strong password"
                icon={KeyIcon}
            >
                <Button
                    variant="outline"
                    onClick={() => setShowPasswordModal(true)}
                >
                    Change Password
                </Button>
            </SettingsSection>

            {/* Active Sessions */}
            <SettingsSection
                title="Active Sessions"
                description="Manage devices where you're currently logged in"
                icon={DevicePhoneMobileIcon}
            >
                {sessionsLoading ? (
                    <div className="space-y-3">
                        {[1, 2].map((i) => (
                            <div key={i} className="animate-pulse flex items-center gap-4 p-4 bg-neutral-50 rounded-xl">
                                <div className="w-10 h-10 bg-neutral-200 rounded-lg" />
                                <div className="flex-1">
                                    <div className="h-4 bg-neutral-200 rounded w-1/3 mb-2" />
                                    <div className="h-3 bg-neutral-200 rounded w-1/2" />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="space-y-3">
                        {sessions.map((session) => (
                            <div
                                key={session.id}
                                className={cn(
                                    'flex items-center gap-4 p-4 rounded-xl',
                                    session.isCurrent ? 'bg-primary-50 border border-primary-200' : 'bg-neutral-50'
                                )}
                            >
                                <div className={cn(
                                    'w-10 h-10 rounded-lg flex items-center justify-center',
                                    session.isCurrent ? 'bg-primary-100' : 'bg-neutral-200'
                                )}>
                                    {session.device.includes('iPhone') || session.device.includes('Android') ? (
                                        <DevicePhoneMobileIcon className={cn('w-5 h-5', session.isCurrent ? 'text-primary-600' : 'text-neutral-500')} />
                                    ) : (
                                        <ComputerDesktopIcon className={cn('w-5 h-5', session.isCurrent ? 'text-primary-600' : 'text-neutral-500')} />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <p className="font-medium text-neutral-900">{session.device}</p>
                                        {session.isCurrent && (
                                            <span className="text-xs font-medium text-primary-600 bg-primary-100 px-2 py-0.5 rounded-full">
                        Current
                      </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-neutral-500">
                                        {session.location} • {formatDistanceToNow(new Date(session.lastActive), { addSuffix: true })}
                                    </p>
                                </div>
                                {!session.isCurrent && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleRevokeSession(session.id)}
                                        loading={isRevoking}
                                        className="text-crisis-600 hover:bg-crisis-50"
                                    >
                                        Revoke
                                    </Button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </SettingsSection>

            {/* Change Password Modal */}
            <Modal
                isOpen={showPasswordModal}
                onClose={() => setShowPasswordModal(false)}
                title="Change Password"
                size="md"
            >
                <form onSubmit={handleSubmit(handlePasswordSubmit)} className="space-y-4">
                    <Input
                        label="Current Password"
                        type="password"
                        {...register('currentPassword')}
                        error={errors.currentPassword?.message}
                    />

                    <div>
                        <Input
                            label="New Password"
                            type="password"
                            {...register('newPassword')}
                            error={errors.newPassword?.message}
                        />
                        {watchPassword && (
                            <PasswordStrength password={watchPassword} className="mt-2" />
                        )}
                    </div>

                    <Input
                        label="Confirm New Password"
                        type="password"
                        {...register('confirmNewPassword')}
                        error={errors.confirmNewPassword?.message}
                    />

                    <div className="flex justify-end gap-3 pt-4">
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => setShowPasswordModal(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            variant="primary"
                            loading={isChangingPassword}
                        >
                            Update Password
                        </Button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}

export default SecuritySettings;
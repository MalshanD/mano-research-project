import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import profileService from '../services/profileService';
import { useNotification } from '../contexts/NotificationContext';

export function useProfile() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useNotification();

    // Get profile
    const {
        data: profile,
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ['profile'],
        queryFn: profileService.getProfile,
    });

    // Update profile mutation
    const updateProfileMutation = useMutation({
        mutationFn: profileService.updateProfile,
        onSuccess: (data) => {
            queryClient.setQueryData(['profile'], data);
            showSuccess('Profile updated successfully');
        },
        onError: (error) => {
            showError(error.message || 'Failed to update profile');
        },
    });

    // Update avatar mutation
    const updateAvatarMutation = useMutation({
        mutationFn: profileService.updateAvatar,
        onSuccess: (data) => {
            queryClient.setQueryData(['profile'], (old) => ({
                ...old,
                avatar: data.avatar,
            }));
            showSuccess('Avatar updated successfully');
        },
        onError: (error) => {
            showError(error.message || 'Failed to update avatar');
        },
    });

    // Delete avatar mutation
    const deleteAvatarMutation = useMutation({
        mutationFn: profileService.deleteAvatar,
        onSuccess: () => {
            queryClient.setQueryData(['profile'], (old) => ({
                ...old,
                avatar: null,
            }));
            showSuccess('Avatar removed');
        },
        onError: (error) => {
            showError(error.message || 'Failed to remove avatar');
        },
    });

    // Helper functions
    const updateProfile = useCallback((data) => {
        return updateProfileMutation.mutateAsync(data);
    }, [updateProfileMutation]);

    const updateAvatar = useCallback((file) => {
        return updateAvatarMutation.mutateAsync(file);
    }, [updateAvatarMutation]);

    const deleteAvatar = useCallback(() => {
        return deleteAvatarMutation.mutateAsync();
    }, [deleteAvatarMutation]);

    return {
        profile,
        isLoading,
        error,
        refetch,
        updateProfile,
        updateAvatar,
        deleteAvatar,
        isUpdating: updateProfileMutation.isPending,
        isUploadingAvatar: updateAvatarMutation.isPending,
    };
}

export function useSettings() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useNotification();

    // Get settings
    const {
        data: settings,
        isLoading,
        error,
    } = useQuery({
        queryKey: ['settings'],
        queryFn: profileService.getSettings,
    });

    // Update settings mutation
    const updateSettingsMutation = useMutation({
        mutationFn: ({ category, data }) => profileService.updateSettings(category, data),
        onSuccess: (data) => {
            queryClient.setQueryData(['settings'], data);
            showSuccess('Settings updated');
        },
        onError: (error) => {
            showError(error.message || 'Failed to update settings');
        },
    });

    // Change password mutation
    const changePasswordMutation = useMutation({
        mutationFn: ({ currentPassword, newPassword }) =>
            profileService.changePassword(currentPassword, newPassword),
        onSuccess: () => {
            showSuccess('Password changed successfully');
        },
        onError: (error) => {
            showError(error.message || 'Failed to change password');
        },
    });

    // Export data mutation
    const exportDataMutation = useMutation({
        mutationFn: profileService.exportData,
        onSuccess: (data) => {
            showSuccess('Data export started. You will receive a download link shortly.');
            return data;
        },
        onError: (error) => {
            showError(error.message || 'Failed to export data');
        },
    });

    // Delete account mutation
    const deleteAccountMutation = useMutation({
        mutationFn: profileService.deleteAccount,
        onSuccess: () => {
            showSuccess('Account deleted');
        },
        onError: (error) => {
            showError(error.message || 'Failed to delete account');
        },
    });

    // Helper functions
    const updateSettings = useCallback((category, data) => {
        return updateSettingsMutation.mutateAsync({ category, data });
    }, [updateSettingsMutation]);

    const changePassword = useCallback((currentPassword, newPassword) => {
        return changePasswordMutation.mutateAsync({ currentPassword, newPassword });
    }, [changePasswordMutation]);

    const exportData = useCallback(() => {
        return exportDataMutation.mutateAsync();
    }, [exportDataMutation]);

    const deleteAccount = useCallback((password) => {
        return deleteAccountMutation.mutateAsync(password);
    }, [deleteAccountMutation]);

    return {
        settings,
        isLoading,
        error,
        updateSettings,
        changePassword,
        exportData,
        deleteAccount,
        isUpdating: updateSettingsMutation.isPending,
        isChangingPassword: changePasswordMutation.isPending,
        isExporting: exportDataMutation.isPending,
        isDeleting: deleteAccountMutation.isPending,
    };
}

export function useActivityLog() {
    return useQuery({
        queryKey: ['activityLog'],
        queryFn: () => profileService.getActivityLog(),
    });
}

export function useSessions() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useNotification();

    const {
        data: sessions = [],
        isLoading,
    } = useQuery({
        queryKey: ['sessions'],
        queryFn: profileService.getSessions,
    });

    const revokeSessionMutation = useMutation({
        mutationFn: profileService.revokeSession,
        onSuccess: () => {
            queryClient.invalidateQueries(['sessions']);
            showSuccess('Session revoked');
        },
        onError: (error) => {
            showError(error.message || 'Failed to revoke session');
        },
    });

    const revokeSession = useCallback((sessionId) => {
        return revokeSessionMutation.mutateAsync(sessionId);
    }, [revokeSessionMutation]);

    return {
        sessions,
        isLoading,
        revokeSession,
        isRevoking: revokeSessionMutation.isPending,
    };
}

export default useProfile;
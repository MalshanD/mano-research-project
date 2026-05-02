import { useState } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card, Tabs, Alert } from '../../components/common';
import {
    SettingsSection,
    ThemeSelector,
    NotificationSettings,
    PrivacySettings,
    SecuritySettings,
    DangerZone,
} from '../../components/features/settings';
import { useSettings } from '../../hooks/useProfile';
import { useTheme } from '../../contexts/ThemeContext';
import {
    BellIcon,
    ShieldCheckIcon,
    PaintBrushIcon,
    KeyIcon,
    Cog6ToothIcon,
    ExclamationTriangleIcon,
    EyeIcon,
    GlobeAltIcon,
} from '@heroicons/react/24/outline';

function Settings() {
    const {
        settings,
        isLoading,
        updateSettings,
        changePassword,
        exportData,
        deleteAccount,
        isUpdating,
        isChangingPassword,
        isExporting,
        isDeleting,
    } = useSettings();

    const { theme, setTheme } = useTheme();

    const tabs = [
        {
            id: 'notifications',
            label: 'Notifications',
            icon: <BellIcon className="w-4 h-4" />,
            content: (
                <NotificationSettings
                    settings={settings?.notifications}
                    onUpdate={updateSettings}
                    isUpdating={isUpdating}
                />
            ),
        },
        {
            id: 'privacy',
            label: 'Privacy',
            icon: <ShieldCheckIcon className="w-4 h-4" />,
            content: (
                <PrivacySettings
                    settings={settings?.privacy}
                    onUpdate={updateSettings}
                    isUpdating={isUpdating}
                />
            ),
        },
        {
            id: 'appearance',
            label: 'Appearance',
            icon: <PaintBrushIcon className="w-4 h-4" />,
            content: (
                <div className="space-y-6">
                    <SettingsSection
                        title="Theme"
                        description="Choose your preferred color scheme"
                        icon={PaintBrushIcon}
                    >
                        <ThemeSelector />
                    </SettingsSection>

                    <SettingsSection
                        title="Display"
                        description="Customize how content is displayed"
                        icon={EyeIcon}
                    >
                        <div className="space-y-4">
                            {/* Font Size */}
                            <div>
                                <label className="block text-sm font-medium text-neutral-700 mb-2">
                                    Font Size
                                </label>
                                <div className="flex gap-2">
                                    {['small', 'medium', 'large'].map((size) => (
                                        <button
                                            key={size}
                                            className={cn(
                                                'px-4 py-2 rounded-2xl border-2 text-sm font-medium capitalize transition-all',
                                                settings?.display?.fontSize === size
                                                    ? 'border-terracotta bg-cream text-terracotta'
                                                    : 'border-sand/40 hover:border-sand'
                                            )}
                                            onClick={() => updateSettings('display', { fontSize: size })}
                                        >
                                            {size}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Reduced Motion */}
                            <div className="flex items-center justify-between py-3">
                                <div>
                                    <p className="font-medium text-neutral-900">Reduced Motion</p>
                                    <p className="text-sm text-neutral-500">Minimize animations</p>
                                </div>
                                <button
                                    onClick={() => updateSettings('display', { reducedMotion: !settings?.display?.reducedMotion })}
                                    className={cn(
                                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                                        settings?.display?.reducedMotion ? 'bg-terracotta' : 'bg-sand'
                                    )}
                                >
                  <span
                      className={cn(
                          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                          settings?.display?.reducedMotion ? 'translate-x-6' : 'translate-x-1'
                      )}
                  />
                                </button>
                            </div>
                        </div>
                    </SettingsSection>
                </div>
            ),
        },
        {
            id: 'security',
            label: 'Security',
            icon: <KeyIcon className="w-4 h-4" />,
            content: (
                <SecuritySettings
                    onChangePassword={changePassword}
                    isChangingPassword={isChangingPassword}
                />
            ),
        },
        {
            id: 'account',
            label: 'Account',
            icon: <Cog6ToothIcon className="w-4 h-4" />,
            content: (
                <div className="space-y-6">
                    {/* Language */}
                    <SettingsSection
                        title="Language & Region"
                        description="Set your language and regional preferences"
                        icon={GlobeAltIcon}
                    >
                        <div>
                            <label className="block text-sm font-medium text-neutral-700 mb-2">
                                Language
                            </label>
                            <select
                                className="w-full px-4 py-2 border border-sand/40 rounded-2xl focus:ring-2 focus:ring-peach/50 focus:border-terracotta-light"
                                value={settings?.language || 'en'}
                                onChange={(e) => updateSettings('display', { language: e.target.value })}
                            >
                                <option value="en">English</option>
                                <option value="es">Español</option>
                                <option value="fr">Français</option>
                                <option value="de">Deutsch</option>
                                <option value="pt">Português</option>
                            </select>
                        </div>
                    </SettingsSection>

                    {/* Danger Zone */}
                    <DangerZone
                        onExportData={exportData}
                        onDeleteAccount={deleteAccount}
                        isExporting={isExporting}
                        isDeleting={isDeleting}
                    />
                </div>
            ),
        },
    ];

    if (isLoading) {
        return (
            <PageContainer title="Settings">
                <div className="animate-pulse space-y-6">
                    <div className="h-12 bg-sand/30 rounded-2xl w-full max-w-md" />
                    <div className="h-64 bg-sand/30 rounded-3xl" />
                    <div className="h-64 bg-sand/30 rounded-3xl" />
                </div>
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title="Settings"
            subtitle="Manage your preferences and account settings"
        >
            <Tabs tabs={tabs} defaultTab="notifications" variant="pills" orientation="vertical" />
        </PageContainer>
    );
}

// Helper
function cn(...classes) {
    return classes.filter(Boolean).join(' ');
}

export default Settings;
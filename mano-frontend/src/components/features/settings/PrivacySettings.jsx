import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import SettingsSection from './SettingsSection';
import SettingsToggle from './SettingsToggle';
import { Select } from '../../common';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';

const visibilityOptions = [
    { value: 'public', label: 'Public - Anyone can see your profile' },
    { value: 'community', label: 'Community - Only community members can see' },
    { value: 'private', label: 'Private - Only you can see your profile' },
];

function PrivacySettings({
                             settings,
                             onUpdate,
                             isUpdating = false,
                         }) {
    const [localSettings, setLocalSettings] = useState(settings);

    const handleToggle = async (key, value) => {
        const newSettings = {
            ...localSettings,
            [key]: value,
        };
        setLocalSettings(newSettings);
        await onUpdate('privacy', newSettings);
    };

    const handleVisibilityChange = async (value) => {
        const newSettings = {
            ...localSettings,
            profileVisibility: value,
        };
        setLocalSettings(newSettings);
        await onUpdate('privacy', newSettings);
    };

    return (
        <SettingsSection
            title="Privacy Settings"
            description="Control who can see your information and how it's used"
            icon={ShieldCheckIcon}
        >
            <div className="space-y-6">
                {/* Profile Visibility */}
                <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Profile Visibility
                    </label>
                    <Select
                        options={visibilityOptions}
                        value={localSettings?.profileVisibility || 'community'}
                        onChange={(e) => handleVisibilityChange(e.target.value)}
                        disabled={isUpdating}
                    />
                </div>

                {/* Toggle Settings */}
                <div className="divide-y divide-neutral-100">
                    <SettingsToggle
                        label="Show Online Status"
                        description="Let others see when you're online"
                        checked={localSettings?.showOnlineStatus ?? true}
                        onChange={(value) => handleToggle('showOnlineStatus', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Allow Messages"
                        description="Let community members send you messages"
                        checked={localSettings?.allowMessages ?? true}
                        onChange={(value) => handleToggle('allowMessages', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Share Data for Research"
                        description="Anonymously contribute to mental health research"
                        checked={localSettings?.shareDataForResearch ?? false}
                        onChange={(value) => handleToggle('shareDataForResearch', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Analytics"
                        description="Help us improve by sharing usage data"
                        checked={localSettings?.allowAnalytics ?? true}
                        onChange={(value) => handleToggle('allowAnalytics', value)}
                        disabled={isUpdating}
                    />
                </div>
            </div>
        </SettingsSection>
    );
}

export default PrivacySettings;
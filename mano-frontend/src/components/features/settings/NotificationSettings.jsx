import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import SettingsSection from './SettingsSection';
import SettingsToggle from './SettingsToggle';
import { BellIcon, EnvelopeIcon, DevicePhoneMobileIcon } from '@heroicons/react/24/outline';

function NotificationSettings({
                                  settings,
                                  onUpdate,
                                  isUpdating = false,
                              }) {
    const [localSettings, setLocalSettings] = useState(settings);

    const handleToggle = async (category, key, value) => {
        const newSettings = {
            ...localSettings,
            [category]: {
                ...localSettings[category],
                [key]: value,
            },
        };
        setLocalSettings(newSettings);
        await onUpdate('notifications', newSettings);
    };

    return (
        <div className="space-y-6">
            {/* Email Notifications */}
            <SettingsSection
                title="Email Notifications"
                description="Choose what emails you'd like to receive"
                icon={EnvelopeIcon}
            >
                <div className="divide-y divide-neutral-100">
                    <SettingsToggle
                        label="Assessment Reminders"
                        description="Reminders to complete your regular assessments"
                        checked={localSettings?.email?.assessmentReminders ?? true}
                        onChange={(value) => handleToggle('email', 'assessmentReminders', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Weekly Report"
                        description="A summary of your progress each week"
                        checked={localSettings?.email?.weeklyReport ?? true}
                        onChange={(value) => handleToggle('email', 'weeklyReport', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Community Activity"
                        description="Updates about activity in your community"
                        checked={localSettings?.email?.communityActivity ?? true}
                        onChange={(value) => handleToggle('email', 'communityActivity', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Product Updates"
                        description="News about new features and improvements"
                        checked={localSettings?.email?.productUpdates ?? false}
                        onChange={(value) => handleToggle('email', 'productUpdates', value)}
                        disabled={isUpdating}
                    />
                </div>
            </SettingsSection>

            {/* Push Notifications */}
            <SettingsSection
                title="Push Notifications"
                description="Notifications on your device"
                icon={BellIcon}
            >
                <div className="divide-y divide-neutral-100">
                    <SettingsToggle
                        label="Chat Messages"
                        description="New messages from Manō"
                        checked={localSettings?.push?.chatMessages ?? true}
                        onChange={(value) => handleToggle('push', 'chatMessages', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Crisis Alerts"
                        description="Important wellness alerts"
                        checked={localSettings?.push?.crisisAlerts ?? true}
                        onChange={(value) => handleToggle('push', 'crisisAlerts', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Activity Reminders"
                        description="Reminders to complete daily activities"
                        checked={localSettings?.push?.activityReminders ?? true}
                        onChange={(value) => handleToggle('push', 'activityReminders', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Peer Messages"
                        description="Messages from community members"
                        checked={localSettings?.push?.peerMessages ?? true}
                        onChange={(value) => handleToggle('push', 'peerMessages', value)}
                        disabled={isUpdating}
                    />
                </div>
            </SettingsSection>

            {/* SMS Notifications */}
            <SettingsSection
                title="SMS Notifications"
                description="Text message alerts (standard rates may apply)"
                icon={DevicePhoneMobileIcon}
            >
                <div className="divide-y divide-neutral-100">
                    <SettingsToggle
                        label="Crisis Alerts"
                        description="Emergency alerts via text message"
                        checked={localSettings?.sms?.crisisAlerts ?? true}
                        onChange={(value) => handleToggle('sms', 'crisisAlerts', value)}
                        disabled={isUpdating}
                    />
                    <SettingsToggle
                        label="Appointment Reminders"
                        description="Reminders for scheduled sessions"
                        checked={localSettings?.sms?.appointmentReminders ?? false}
                        onChange={(value) => handleToggle('sms', 'appointmentReminders', value)}
                        disabled={isUpdating}
                    />
                </div>
            </SettingsSection>
        </div>
    );
}

export default NotificationSettings;
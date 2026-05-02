import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { profileSchema } from '../../../utils/validations';
import { cn } from '../../../utils/helpers';
import { Button, Input, Textarea, Select, Card } from '../../common';

const genderOptions = [
    { value: '', label: 'Select gender' },
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
    { value: 'non_binary', label: 'Non-binary' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

const timezoneOptions = [
    { value: 'America/New_York', label: 'Eastern Time (ET)' },
    { value: 'America/Chicago', label: 'Central Time (CT)' },
    { value: 'America/Denver', label: 'Mountain Time (MT)' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
    { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
    { value: 'Pacific/Honolulu', label: 'Hawaii Time (HT)' },
    { value: 'Europe/London', label: 'Greenwich Mean Time (GMT)' },
    { value: 'Europe/Paris', label: 'Central European Time (CET)' },
    { value: 'Asia/Tokyo', label: 'Japan Standard Time (JST)' },
    { value: 'Australia/Sydney', label: 'Australian Eastern Time (AET)' },
];

function ProfileForm({
                         profile,
                         onSubmit,
                         onCancel,
                         isSubmitting = false,
                         className,
                     }) {
    const {
        register,
        handleSubmit,
        formState: { errors, isDirty },
    } = useForm({
        resolver: yupResolver(profileSchema),
        defaultValues: {
            firstName: profile?.firstName || '',
            lastName: profile?.lastName || '',
            phone: profile?.phone || '',
            dateOfBirth: profile?.dateOfBirth || '',
            gender: profile?.gender || '',
            bio: profile?.bio || '',
            location: profile?.location || '',
            timezone: profile?.timezone || 'America/Los_Angeles',
            emergencyContactName: profile?.emergencyContact?.name || '',
            emergencyContactPhone: profile?.emergencyContact?.phone || '',
            emergencyContactRelationship: profile?.emergencyContact?.relationship || '',
        },
    });

    const onFormSubmit = (data) => {
        const formattedData = {
            firstName: data.firstName,
            lastName: data.lastName,
            phone: data.phone,
            dateOfBirth: data.dateOfBirth,
            gender: data.gender,
            bio: data.bio,
            location: data.location,
            timezone: data.timezone,
            emergencyContact: {
                name: data.emergencyContactName,
                phone: data.emergencyContactPhone,
                relationship: data.emergencyContactRelationship,
            },
        };
        onSubmit(formattedData);
    };

    return (
        <form onSubmit={handleSubmit(onFormSubmit)} className={cn('space-y-6', className)}>
            {/* Basic Info */}
            <Card>
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">Basic Information</h3>

                <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                        label="First Name"
                        {...register('firstName')}
                        error={errors.firstName?.message}
                    />
                    <Input
                        label="Last Name"
                        {...register('lastName')}
                        error={errors.lastName?.message}
                    />
                </div>

                <div className="grid gap-4 sm:grid-cols-2 mt-4">
                    <Input
                        label="Phone Number"
                        type="tel"
                        {...register('phone')}
                        error={errors.phone?.message}
                        placeholder="+1 (555) 123-4567"
                    />
                    <Input
                        label="Date of Birth"
                        type="date"
                        {...register('dateOfBirth')}
                        error={errors.dateOfBirth?.message}
                    />
                </div>

                <div className="grid gap-4 sm:grid-cols-2 mt-4">
                    <Select
                        label="Gender"
                        options={genderOptions}
                        {...register('gender')}
                        error={errors.gender?.message}
                    />
                    <Input
                        label="Location"
                        {...register('location')}
                        error={errors.location?.message}
                        placeholder="City, State"
                    />
                </div>

                <div className="mt-4">
                    <Select
                        label="Timezone"
                        options={timezoneOptions}
                        {...register('timezone')}
                        error={errors.timezone?.message}
                    />
                </div>

                <div className="mt-4">
                    <Textarea
                        label="Bio"
                        {...register('bio')}
                        error={errors.bio?.message}
                        placeholder="Tell us a bit about yourself..."
                        rows={3}
                        maxLength={500}
                    />
                </div>
            </Card>

            {/* Emergency Contact */}
            <Card>
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">Emergency Contact</h3>
                <p className="text-sm text-neutral-500 mb-4">
                    This information will only be used in case of emergency.
                </p>

                <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                        label="Contact Name"
                        {...register('emergencyContactName')}
                        error={errors.emergencyContactName?.message}
                        placeholder="Full name"
                    />
                    <Input
                        label="Relationship"
                        {...register('emergencyContactRelationship')}
                        error={errors.emergencyContactRelationship?.message}
                        placeholder="e.g., Parent, Sibling, Friend"
                    />
                </div>

                <div className="mt-4">
                    <Input
                        label="Contact Phone"
                        type="tel"
                        {...register('emergencyContactPhone')}
                        error={errors.emergencyContactPhone?.message}
                        placeholder="+1 (555) 123-4567"
                    />
                </div>
            </Card>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3">
                <Button type="button" variant="ghost" onClick={onCancel}>
                    Cancel
                </Button>
                <Button
                    type="submit"
                    variant="primary"
                    loading={isSubmitting}
                    disabled={!isDirty}
                >
                    Save Changes
                </Button>
            </div>
        </form>
    );
}

export default ProfileForm;
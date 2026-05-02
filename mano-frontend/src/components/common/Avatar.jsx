import { cn, getInitials } from '../../utils/helpers';

const sizes = {
    xs: 'w-6 h-6 text-xs',
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-base',
    lg: 'w-12 h-12 text-lg',
    xl: 'w-16 h-16 text-xl',
    '2xl': 'w-20 h-20 text-2xl',
};

const colors = [
    'bg-primary-500',
    'bg-accent-500',
    'bg-success-500',
    'bg-warning-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
    'bg-teal-500',
];

function Avatar({
                    src,
                    alt,
                    firstName,
                    lastName,
                    size = 'md',
                    className,
                    status,
                    statusPosition = 'bottom-right',
                    ...props
                }) {
    // Generate consistent color based on name
    const getColorFromName = (first, last) => {
        const name = `${first || ''}${last || ''}`;
        const index = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return colors[index % colors.length];
    };

    const initials = getInitials(firstName, lastName);
    const bgColor = getColorFromName(firstName, lastName);

    const statusColors = {
        online: 'bg-success-500',
        offline: 'bg-neutral-400',
        away: 'bg-warning-500',
        busy: 'bg-crisis-500',
    };

    const statusPositions = {
        'top-right': 'top-0 right-0',
        'top-left': 'top-0 left-0',
        'bottom-right': 'bottom-0 right-0',
        'bottom-left': 'bottom-0 left-0',
    };

    return (
        <div className={cn('relative inline-flex', className)} {...props}>
            {src ? (
                <img
                    src={src}
                    alt={alt || `${firstName} ${lastName}`}
                    className={cn(
                        'rounded-full object-cover ring-2 ring-white',
                        sizes[size]
                    )}
                />
            ) : (
                <div
                    className={cn(
                        'rounded-full flex items-center justify-center font-medium text-white ring-2 ring-white',
                        sizes[size],
                        bgColor
                    )}
                >
                    {initials}
                </div>
            )}

            {status && (
                <span
                    className={cn(
                        'absolute block rounded-full ring-2 ring-white',
                        size === 'xs' || size === 'sm' ? 'w-2 h-2' : 'w-3 h-3',
                        statusColors[status],
                        statusPositions[statusPosition]
                    )}
                />
            )}
        </div>
    );
}

// Avatar Group component
export function AvatarGroup({ avatars = [], max = 4, size = 'md' }) {
    const displayedAvatars = avatars.slice(0, max);
    const remainingCount = avatars.length - max;

    return (
        <div className="flex -space-x-2">
            {displayedAvatars.map((avatar, index) => (
                <Avatar
                    key={index}
                    src={avatar.src}
                    firstName={avatar.firstName}
                    lastName={avatar.lastName}
                    size={size}
                    className="ring-2 ring-white"
                />
            ))}
            {remainingCount > 0 && (
                <div
                    className={cn(
                        'rounded-full flex items-center justify-center font-medium bg-neutral-100 text-neutral-600 ring-2 ring-white',
                        sizes[size]
                    )}
                >
                    +{remainingCount}
                </div>
            )}
        </div>
    );
}

export default Avatar;
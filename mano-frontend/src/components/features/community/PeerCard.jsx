import { cn } from '../../../utils/helpers';
import { Avatar, Badge, Button } from '../../common';
import { ChatBubbleLeftIcon, UserPlusIcon, UserMinusIcon } from '@heroicons/react/24/outline';
import { formatDistanceToNow } from 'date-fns';

function PeerCard({
                      peer,
                      onMessage,
                      onConnect,
                      onDisconnect,
                      onClick,
                      isConnected = false,
                      compact = false,
                      showLastActive = true,
                      className,
                  }) {
    const {
        id,
        firstName,
        lastName,
        avatar,
        clusterName,
        commonInterests = [],
        lastActive,
        status = 'offline',
        bio,
    } = peer || {};

    if (compact) {
        return (
            <div
                onClick={onClick}
                className={cn(
                    'flex items-center gap-3 p-3 bg-white rounded-xl border border-neutral-100 transition-all',
                    onClick && 'cursor-pointer hover:shadow-soft',
                    className
                )}
            >
                <Avatar
                    src={avatar}
                    firstName={firstName}
                    lastName={lastName}
                    size="sm"
                    status={status}
                />
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-900 truncate">
                        {firstName} {lastName?.charAt(0)}.
                    </p>
                    <p className="text-xs text-neutral-500">{clusterName}</p>
                </div>
                <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={(e) => {
                        e.stopPropagation();
                        onMessage?.(peer);
                    }}
                >
                    <ChatBubbleLeftIcon className="w-4 h-4" />
                </Button>
            </div>
        );
    }

    return (
        <div
            onClick={onClick}
            className={cn(
                'bg-white rounded-2xl border border-neutral-100 p-5 transition-all',
                onClick && 'cursor-pointer hover:shadow-soft',
                className
            )}
        >
            <div className="flex items-start gap-4">
                <Avatar
                    src={avatar}
                    firstName={firstName}
                    lastName={lastName}
                    size="lg"
                    status={status}
                />
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <div>
                            <h3 className="font-semibold text-neutral-900">
                                {firstName} {lastName?.charAt(0)}.
                            </h3>
                            <p className="text-sm text-neutral-500">{clusterName} Community</p>
                        </div>
                        {isConnected && (
                            <Badge variant="success" size="sm">Connected</Badge>
                        )}
                    </div>

                    {/* Bio */}
                    {bio && (
                        <p className="text-sm text-neutral-600 mt-2 line-clamp-2">{bio}</p>
                    )}

                    {/* Common Interests */}
                    {commonInterests.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                            {commonInterests.slice(0, 3).map((interest, index) => (
                                <span
                                    key={index}
                                    className="px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-full"
                                >
                  {interest}
                </span>
                            ))}
                            {commonInterests.length > 3 && (
                                <span className="px-2 py-0.5 bg-neutral-100 text-neutral-500 text-xs rounded-full">
                  +{commonInterests.length - 3} more
                </span>
                            )}
                        </div>
                    )}

                    {/* Last Active */}
                    {showLastActive && lastActive && status !== 'online' && (
                        <p className="text-xs text-neutral-400 mt-2">
                            Active {formatDistanceToNow(new Date(lastActive), { addSuffix: true })}
                        </p>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 mt-4">
                        <Button
                            variant="primary"
                            size="sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                onMessage?.(peer);
                            }}
                            leftIcon={<ChatBubbleLeftIcon className="w-4 h-4" />}
                        >
                            Message
                        </Button>
                        {!isConnected ? (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onConnect?.(peer);
                                }}
                                leftIcon={<UserPlusIcon className="w-4 h-4" />}
                            >
                                Connect
                            </Button>
                        ) : onDisconnect && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDisconnect?.(peer);
                                }}
                                leftIcon={<UserMinusIcon className="w-4 h-4" />}
                                className="text-neutral-500"
                            >
                                Disconnect
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default PeerCard;
import { useState } from 'react';
import { format } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Avatar } from '../../common';
import { PERSONAS } from './PersonaSelector';
import {
    CheckIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    ClipboardIcon,
    HandThumbUpIcon,
    HandThumbDownIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

function ChatBubble({
                        message,
                        isUser = false,
                        showAvatar = true,
                        showTimestamp = true,
                        showFeedback = false,
                        onFeedback,
                        onCopy,
                        user,
                        className,
                    }) {
    const [copied, setCopied] = useState(false);
    const [feedback, setFeedback] = useState(null);

    const {
        content,
        timestamp,
        status = 'sent', // sending, sent, delivered, read, error
        type = 'text',
        metadata,
    } = message;

    const personaInfo = !isUser && metadata?.persona
        ? PERSONAS.find((p) => p.id === metadata.persona) || null
        : null;

    const handleCopy = async () => {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        onCopy?.(message);
    };

    const handleFeedback = (type) => {
        setFeedback(type);
        onFeedback?.(message, type);
    };

    const StatusIcon = () => {
        switch (status) {
            case 'sending':
                return <span className="w-3 h-3 rounded-full border-2 border-neutral-300 border-t-transparent animate-spin" />;
            case 'sent':
                return <CheckIcon className="w-3.5 h-3.5 text-neutral-400" />;
            case 'delivered':
                return <CheckCircleIcon className="w-3.5 h-3.5 text-neutral-400" />;
            case 'read':
                return <CheckCircleSolidIcon className="w-3.5 h-3.5 text-primary-500" />;
            case 'error':
                return <ExclamationCircleIcon className="w-3.5 h-3.5 text-crisis-500" />;
            default:
                return null;
        }
    };

    return (
        <div
            className={cn(
                'flex gap-3 max-w-[85%] group',
                isUser ? 'ml-auto flex-row-reverse' : 'mr-auto',
                className
            )}
        >
            {/* Avatar */}
            {showAvatar && (
                <div className="flex-shrink-0 mt-1">
                    {isUser ? (
                        <Avatar
                            src={user?.avatar}
                            firstName={user?.firstName}
                            lastName={user?.lastName}
                            size="sm"
                        />
                    ) : (
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                            <span className="text-xs font-bold text-white font-display">M</span>
                        </div>
                    )}
                </div>
            )}

            <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
                {/* Message Bubble */}
                <div
                    className={cn(
                        'px-4 py-3 rounded-2xl relative',
                        isUser
                            ? 'bg-primary-500 text-white rounded-tr-md'
                            : 'bg-white shadow-soft border border-neutral-100 rounded-tl-md',
                        status === 'error' && 'bg-crisis-50 border-crisis-200'
                    )}
                >
                    {/* Message Content */}
                    {type === 'text' && (
                        <p className={cn('text-sm whitespace-pre-wrap break-words', isUser ? 'text-white' : 'text-neutral-800')}>
                            {content}
                        </p>
                    )}

                    {/* Typing Indicator */}
                    {type === 'typing' && (
                        <div className="flex items-center gap-1 py-1 px-2">
                            <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                    )}

                    {/* Persona Badge */}
                    {personaInfo && (
                        <div className={cn(
                            'inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded-full border text-xs font-semibold',
                            personaInfo.pill
                        )}>
                            <span>{personaInfo.emoji}</span>
                            <span>{personaInfo.label}</span>
                        </div>
                    )}

                    {/* Crisis Alert */}
                    {metadata?.crisisDetected && (
                        <div className="mt-2 pt-2 border-t border-crisis-200">
                            <p className="text-xs text-crisis-600 font-medium">
                                🆘 Crisis support resources are available
                            </p>
                        </div>
                    )}
                </div>

                {/* Message Footer */}
                <div className={cn('flex items-center gap-2 mt-1 px-1', isUser ? 'flex-row-reverse' : '')}>
                    {/* Timestamp */}
                    {showTimestamp && timestamp && (
                        <span className="text-xs text-neutral-400">
              {format(new Date(timestamp), 'h:mm a')}
            </span>
                    )}

                    {/* Status */}
                    {isUser && <StatusIcon />}

                    {/* Actions (show on hover for AI messages) */}
                    {!isUser && type === 'text' && (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={handleCopy}
                                className="p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
                                title="Copy message"
                            >
                                {copied ? (
                                    <CheckCircleIcon className="w-4 h-4 text-success-500" />
                                ) : (
                                    <ClipboardIcon className="w-4 h-4" />
                                )}
                            </button>

                            {showFeedback && (
                                <>
                                    <button
                                        onClick={() => handleFeedback('positive')}
                                        className={cn(
                                            'p-1 rounded transition-colors',
                                            feedback === 'positive'
                                                ? 'text-success-500 bg-success-50'
                                                : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
                                        )}
                                        title="Helpful"
                                    >
                                        <HandThumbUpIcon className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => handleFeedback('negative')}
                                        className={cn(
                                            'p-1 rounded transition-colors',
                                            feedback === 'negative'
                                                ? 'text-crisis-500 bg-crisis-50'
                                                : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
                                        )}
                                        title="Not helpful"
                                    >
                                        <HandThumbDownIcon className="w-4 h-4" />
                                    </button>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Error Message */}
                {status === 'error' && (
                    <p className="text-xs text-crisis-500 mt-1 px-1">
                        Failed to send. Tap to retry.
                    </p>
                )}
            </div>
        </div>
    );
}

export default ChatBubble;
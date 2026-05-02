import { useRef, useEffect, useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Button, Loader } from '../../common';
import ChatBubble from './ChatBubble';
import { ArrowDownIcon } from '@heroicons/react/24/outline';

function ChatWindow({
                        messages = [],
                        user,
                        isLoading = false,
                        isTyping = false,
                        hasMore = false,
                        onLoadMore,
                        onFeedback,
                        className,
                    }) {
    const containerRef = useRef(null);
    const bottomRef = useRef(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (autoScroll && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isTyping, autoScroll]);

    // Handle scroll position for scroll-to-bottom button
    const handleScroll = () => {
        if (containerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
            const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
            setShowScrollButton(!isNearBottom);
            setAutoScroll(isNearBottom);
        }
    };

    const scrollToBottom = () => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        setAutoScroll(true);
    };

    // Group consecutive messages from same sender
    const groupedMessages = messages.reduce((groups, message, index) => {
        const prevMessage = messages[index - 1];
        const isSameSender = prevMessage?.senderId === message.senderId;
        const isCloseInTime =
            prevMessage &&
            new Date(message.timestamp) - new Date(prevMessage.timestamp) < 60000;

        if (isSameSender && isCloseInTime) {
            const lastGroup = groups[groups.length - 1];
            lastGroup.messages.push(message);
        } else {
            groups.push({
                senderId: message.senderId,
                messages: [message],
            });
        }

        return groups;
    }, []);

    return (
        <div className={cn('relative flex flex-col h-full', className)}>
            {/* Messages Container */}
            <div
                ref={containerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
            >
                {/* Load More Button */}
                {hasMore && (
                    <div className="text-center py-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onLoadMore}
                            loading={isLoading}
                        >
                            Load earlier messages
                        </Button>
                    </div>
                )}

                {/* Loading State */}
                {isLoading && messages.length === 0 && (
                    <div className="flex items-center justify-center py-8">
                        <Loader size="lg" />
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mb-4">
                            <span className="text-2xl font-bold text-primary-600 font-display">M</span>
                        </div>
                        <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                            Welcome to Manō Chat
                        </h3>
                        <p className="text-neutral-500 max-w-sm">
                            I'm here to listen and support you. Feel free to share how you're feeling or ask me anything.
                        </p>
                    </div>
                )}

                {/* Message Groups */}
                {groupedMessages.map((group, groupIndex) => (
                    <div key={groupIndex} className="space-y-1">
                        {group.messages.map((message, msgIndex) => (
                            <ChatBubble
                                key={message.id || msgIndex}
                                message={message}
                                isUser={message.senderId === user?.id || message.senderId === 'user'}
                                user={user}
                                showAvatar={msgIndex === 0}
                                showTimestamp={msgIndex === group.messages.length - 1}
                                showFeedback={message.senderId !== user?.id && message.senderId !== 'user'}
                                onFeedback={onFeedback}
                            />
                        ))}
                    </div>
                ))}

                {/* Typing Indicator */}
                {isTyping && (
                    <ChatBubble
                        message={{ type: 'typing' }}
                        isUser={false}
                        showAvatar={true}
                        showTimestamp={false}
                    />
                )}

                {/* Scroll anchor */}
                <div ref={bottomRef} />
            </div>

            {/* Scroll to Bottom Button */}
            {showScrollButton && (
                <button
                    onClick={scrollToBottom}
                    className={cn(
                        'absolute bottom-4 right-4 p-3 bg-white rounded-full shadow-lg',
                        'border border-neutral-200 hover:bg-neutral-50 transition-all',
                        'animate-fade-in'
                    )}
                >
                    <ArrowDownIcon className="w-5 h-5 text-neutral-600" />
                </button>
            )}
        </div>
    );
}

export default ChatWindow;
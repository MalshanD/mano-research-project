import { useState } from 'react';
import { format, isToday, isYesterday, isThisWeek } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Button, Input } from '../../common';
import { ConfirmModal } from '../../common/Modal';
import {
    MagnifyingGlassIcon,
    PlusIcon,
    ChatBubbleLeftRightIcon,
    TrashIcon,
} from '@heroicons/react/24/outline';

function ChatSidebar({
                         conversations = [],
                         activeConversationId,
                         onSelectConversation,
                         onNewConversation,
                         onDeleteConversation,
                         className,
                     }) {
    const [searchQuery, setSearchQuery] = useState('');

    const filteredConversations = conversations.filter((conv) =>
        conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conv.lastMessage?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const groupedConversations = filteredConversations.reduce((groups, conv) => {
        const date = new Date(conv.updatedAt || conv.createdAt);
        let label = 'Older';

        if (isToday(date)) {
            label = 'Today';
        } else if (isYesterday(date)) {
            label = 'Yesterday';
        } else if (isThisWeek(date)) {
            label = 'This Week';
        }

        if (!groups[label]) {
            groups[label] = [];
        }
        groups[label].push(conv);

        return groups;
    }, {});

    const groupOrder = ['Today', 'Yesterday', 'This Week', 'Older'];

    return (
        <div className={cn('flex flex-col h-full bg-neutral-50', className)}>
            {/* Header */}
            <div className="p-4 border-b border-neutral-100">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-neutral-900">Chats</h2>
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={onNewConversation}
                        leftIcon={<PlusIcon className="w-4 h-4" />}
                    >
                        New
                    </Button>
                </div>

                {/* Search */}
                <Input
                    type="search"
                    placeholder="Search conversations..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    leftIcon={<MagnifyingGlassIcon className="w-4 h-4" />}
                    size="sm"
                />
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto">
                {filteredConversations.length === 0 ? (
                    <div className="p-4 text-center">
                        <ChatBubbleLeftRightIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                        <p className="text-sm text-neutral-500">
                            {searchQuery ? 'No conversations found' : 'No conversations yet'}
                        </p>
                        {!searchQuery && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onNewConversation}
                                className="mt-2"
                            >
                                Start a new chat
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="py-2">
                        {groupOrder.map((groupLabel) => {
                            const group = groupedConversations[groupLabel];
                            if (!group || group.length === 0) return null;

                            return (
                                <div key={groupLabel}>
                                    <p className="px-4 py-2 text-xs font-medium text-neutral-400 uppercase">
                                        {groupLabel}
                                    </p>
                                    {group.map((conv) => (
                                        <ConversationItem
                                            key={conv.id}
                                            conversation={conv}
                                            isActive={conv.id === activeConversationId}
                                            onClick={() => onSelectConversation(conv)}
                                            onDelete={() => onDeleteConversation(conv)}
                                        />
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}

function ConversationItem({ conversation, isActive, onClick, onDelete }) {
    const [showConfirm, setShowConfirm] = useState(false);

    return (
        <>
        <div
            onClick={onClick}
            className={cn(
                'group flex items-center gap-3 px-3 py-3 cursor-pointer transition-colors relative',
                isActive ? 'bg-primary-50 border-r-2 border-primary-500' : 'hover:bg-white'
            )}
        >
            {/* Icon */}
            <div
                className={cn(
                    'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
                    isActive ? 'bg-primary-100' : 'bg-neutral-100'
                )}
            >
                <ChatBubbleLeftRightIcon
                    className={cn('w-4 h-4', isActive ? 'text-primary-600' : 'text-neutral-500')}
                />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                    <h3
                        className={cn(
                            'text-sm font-medium truncate',
                            isActive ? 'text-primary-900' : 'text-neutral-900'
                        )}
                    >
                        {conversation.title || 'New Chat'}
                    </h3>
                    <span className="text-xs text-neutral-400 flex-shrink-0 group-hover:hidden">
                        {format(new Date(conversation.updatedAt || conversation.createdAt), 'h:mm a')}
                    </span>
                </div>
                <p className="text-xs text-neutral-500 truncate mt-0.5">
                    {conversation.lastMessage
                        ? (
                            <>
                                {conversation.lastMessageSender === 'USER' && (
                                    <span className="font-medium text-neutral-400">You: </span>
                                )}
                                {conversation.lastMessage}
                            </>
                          )
                        : <span className="italic">No messages yet</span>
                    }
                </p>
            </div>

            {/* Delete Button — visible on hover */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    setShowConfirm(true);
                }}
                className={cn(
                    'flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150',
                    'p-1.5 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-red-50'
                )}
                title="Delete conversation"
            >
                <TrashIcon className="w-4 h-4" />
            </button>
        </div>

        <ConfirmModal
            isOpen={showConfirm}
            onClose={() => setShowConfirm(false)}
            onConfirm={() => {
                setShowConfirm(false);
                onDelete();
            }}
            title="Delete Conversation"
            message={`Are you sure you want to delete "${conversation.title || 'this chat'}"? This action cannot be undone.`}
            confirmText="Delete"
            cancelText="Cancel"
            variant="danger"
        />
        </>
    );
}

export default ChatSidebar;
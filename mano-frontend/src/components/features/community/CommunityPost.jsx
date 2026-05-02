import { useState, useRef, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '../../../utils/helpers';
import { Avatar } from '../../common';
import { togglePostReaction } from '../../../api/client';
import {
    FaceSmileIcon,
    ChatBubbleLeftIcon,
    ShareIcon,
    EllipsisHorizontalIcon,
    FlagIcon,
    PaperAirplaneIcon,
} from '@heroicons/react/24/outline';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { useAuth } from '../../../contexts/AuthContext';

// ─── Reaction Definitions ───────────────────────────────────────────────────
const REACTIONS = [
    { type: 'heart',      emoji: '❤️',  label: 'Love' },
    { type: 'hug',        emoji: '🤗', label: 'Hug' },
    { type: 'celebrate',  emoji: '🎉', label: 'Celebrate' },
    { type: 'insightful', emoji: '💡', label: 'Insightful' },
    { type: 'strength',   emoji: '💪', label: 'Strength' },
    { type: 'laugh',      emoji: '😂', label: 'Haha' },
];

// ─── Reaction Picker (hover/click flyout) ───────────────────────────────────
function ReactionPicker({ onReact, myReactions = [], disabled }) {
    const [open, setOpen] = useState(false);
    const timeout = useRef(null);
    const containerRef = useRef(null);

    const handleMouseEnter = () => {
        clearTimeout(timeout.current);
        setOpen(true);
    };

    const handleMouseLeave = () => {
        timeout.current = setTimeout(() => setOpen(false), 300);
    };

    // Close on outside click
    useEffect(() => {
        const handler = (e) => {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const hasAnyReaction = myReactions.length > 0;

    return (
        <div
            ref={containerRef}
            className="relative"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {/* Trigger button */}
            <button
                onClick={() => setOpen((v) => !v)}
                disabled={disabled}
                className={cn(
                    'flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all',
                    hasAnyReaction
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-neutral-600 hover:bg-neutral-50'
                )}
            >
                <FaceSmileIcon className="w-5 h-5" />
                <span className="text-sm font-medium">React</span>
            </button>

            {/* Picker flyout */}
            <Transition
                show={open}
                as={Fragment}
                enter="transition ease-out duration-150"
                enterFrom="opacity-0 scale-90 translate-y-1"
                enterTo="opacity-100 scale-100 translate-y-0"
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100 scale-100 translate-y-0"
                leaveTo="opacity-0 scale-90 translate-y-1"
            >
                <div className="absolute bottom-full left-0 mb-2 flex gap-1 bg-white rounded-2xl shadow-lg border border-neutral-100 px-2 py-1.5 z-20">
                    {REACTIONS.map((r) => {
                        const isActive = myReactions.includes(r.type);
                        return (
                            <button
                                key={r.type}
                                onClick={() => {
                                    onReact(r.type);
                                    setOpen(false);
                                }}
                                className={cn(
                                    'group relative flex items-center justify-center w-9 h-9 rounded-xl transition-all hover:scale-125',
                                    isActive
                                        ? 'bg-primary-100 ring-2 ring-primary-300'
                                        : 'hover:bg-neutral-100'
                                )}
                                title={r.label}
                            >
                                <span className="text-xl">{r.emoji}</span>
                                {/* Tooltip */}
                                <span className="absolute -top-7 left-1/2 -translate-x-1/2 px-2 py-0.5 text-[10px] font-medium text-white bg-neutral-800 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                                    {r.label}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </Transition>
        </div>
    );
}

// ─── Inline Reaction Chips (shown below post content) ───────────────────────
function ReactionChips({ reactions = [], myReactions = [], onReact }) {
    if (reactions.length === 0) return null;

    return (
        <div className="flex flex-wrap gap-1.5 mb-3">
            {reactions.map((r) => {
                const isActive = myReactions.includes(r.type);
                return (
                    <button
                        key={r.type}
                        onClick={() => onReact(r.type)}
                        className={cn(
                            'flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all border',
                            isActive
                                ? 'bg-primary-50 border-primary-300 text-primary-700 hover:bg-primary-100'
                                : 'bg-neutral-50 border-neutral-200 text-neutral-600 hover:bg-neutral-100 hover:border-neutral-300'
                        )}
                    >
                        <span>{r.emoji}</span>
                        <span>{r.count}</span>
                    </button>
                );
            })}
        </div>
    );
}

// ─── Post Type Styles ───────────────────────────────────────────────────────
const postTypeStyles = {
    milestone: {
        bg: 'bg-success-50',
        border: 'border-success-100',
        badge: '🎉 Milestone',
    },
    reflect: {
        bg: 'bg-primary-50',
        border: 'border-primary-100',
        badge: '💭 Reflection',
    },
    reflection: {
        bg: 'bg-primary-50',
        border: 'border-primary-100',
        badge: '💭 Reflection',
    },
    tip: {
        bg: 'bg-warning-50',
        border: 'border-warning-100',
        badge: '💡 Tip',
    },
    discussion: {
        bg: 'bg-accent-50',
        border: 'border-accent-100',
        badge: '💬 Discussion',
    },
    support: {
        bg: 'bg-crisis-50',
        border: 'border-crisis-100',
        badge: '🤗 Support',
    },
};

// ─── Main Component ─────────────────────────────────────────────────────────
function CommunityPost({
    post,
    onLike,
    onComment,
    onShare,
    onReport,
    onAuthorClick,
    className,
}) {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    // Local reaction state (initialized from server data)
    const [localReactions, setLocalReactions] = useState(post.reactions ?? []);
    const [localMyReactions, setLocalMyReactions] = useState(post.my_reactions ?? []);

    // Local comments state
    const [showComments, setShowComments] = useState(false);
    const [localComments, setLocalComments] = useState([]);
    const [commentInput, setCommentInput] = useState('');

    // Reaction mutation
    const reactionMutation = useMutation({
        mutationFn: async (reactionType) => {
            const { data, error } = await togglePostReaction(post.id, user?.id, reactionType);
            if (error) throw new Error(error);
            return data;
        },
        onMutate: async (reactionType) => {
            // Optimistic update
            const wasActive = localMyReactions.includes(reactionType);

            setLocalMyReactions((prev) =>
                wasActive ? prev.filter((r) => r !== reactionType) : [...prev, reactionType]
            );

            setLocalReactions((prev) => {
                const existing = prev.find((r) => r.type === reactionType);
                if (wasActive) {
                    // Decrement or remove
                    if (existing && existing.count <= 1) {
                        return prev.filter((r) => r.type !== reactionType);
                    }
                    return prev.map((r) =>
                        r.type === reactionType ? { ...r, count: r.count - 1 } : r
                    );
                } else {
                    // Increment or add
                    if (existing) {
                        return prev.map((r) =>
                            r.type === reactionType ? { ...r, count: r.count + 1 } : r
                        );
                    }
                    const def = REACTIONS.find((d) => d.type === reactionType);
                    return [...prev, { type: reactionType, emoji: def?.emoji || '', label: def?.label || '', count: 1 }];
                }
            });
        },
        onSuccess: (data) => {
            // Sync with server response
            if (data) {
                setLocalReactions(data.counts ?? []);
                setLocalMyReactions(data.my_reactions ?? []);
            }
        },
        onError: () => {
            // Revert on error — refetch from server
            setLocalReactions(post.reactions ?? []);
            setLocalMyReactions(post.my_reactions ?? []);
        },
    });

    const handleReact = (reactionType) => {
        if (!user?.id) return;
        reactionMutation.mutate(reactionType);
    };

    const handleToggleComments = () => {
        setShowComments((v) => !v);
        onComment?.(post.id);
    };

    const handleAddComment = () => {
        const text = commentInput.trim();
        if (!text) return;
        setLocalComments((prev) => [
            ...prev,
            {
                id: Date.now(),
                text,
                author: user?.firstName || user?.guest_name || 'You',
                createdAt: new Date().toISOString(),
            },
        ]);
        setCommentInput('');
    };

    const handleCommentKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleAddComment();
        }
    };

    const typeStyle = postTypeStyles[post.type] || postTypeStyles.reflection;
    const totalComments = (post.comments ?? 0) + localComments.length;
    const totalReactions = localReactions.reduce((sum, r) => sum + r.count, 0);

    return (
        <div
            className={cn(
                'bg-white rounded-2xl border border-neutral-100 overflow-hidden',
                className
            )}
        >
            {/* Post Type Badge */}
            <div className={cn('px-4 py-2 text-xs font-medium', typeStyle.bg, typeStyle.border, 'border-b')}>
                {typeStyle.badge}
            </div>

            <div className="p-4">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                    <div
                        className="flex items-center gap-3 cursor-pointer"
                        onClick={() => onAuthorClick?.(post.author)}
                    >
                        <Avatar
                            src={post.author?.avatar}
                            firstName={post.author?.firstName}
                            lastName={post.author?.lastName}
                            size="md"
                            status={post.author?.status}
                        />
                        <div>
                            <p className="font-medium text-neutral-900 hover:text-primary-600 transition-colors">
                                {post.author?.firstName} {post.author?.lastName}
                            </p>
                            <div className="flex items-center gap-2 flex-wrap">
                                <p className="text-xs text-neutral-500">
                                    {post.timestamp
                                        ? formatDistanceToNow(new Date(post.timestamp), { addSuffix: true })
                                        : 'Just now'}
                                </p>
                                {/* Component 4: filter-bubble exploration injection — this post
                                    was promoted into the top-N for serendipity, not pure relevance. */}
                                {post.exploration === true && (
                                    <span
                                        title="Discovery pick: surfaced to broaden your feed beyond the most-relevance posts."
                                        className="inline-flex items-center px-2 py-0.5 rounded-full bg-cream/60 text-terracotta-dark text-[10px] font-semibold border border-sand/40"
                                    >
                                        Discovery
                                    </span>
                                )}
                                {/* Component 4: SHAP-style top driver from feed_explainer. */}
                                {Array.isArray(post.explanations) && post.explanations.length > 0 && (
                                    <span
                                        title={post.explanations
                                            .map((e) => `${e.label || e.group}: ${e.delta >= 0 ? '+' : ''}${(e.delta ?? 0).toFixed(3)}`)
                                            .join('  •  ')}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-mint/30 text-sage-dark text-[10px] font-semibold"
                                    >
                                        Why · {post.explanations[0].label || post.explanations[0].group}
                                    </span>
                                )}
                                {/* Component 4: MC-Dropout uncertainty on the feed ranker score. */}
                                {(post.uncertainty?.std != null || post.std != null) && (
                                    <span
                                        title={`Ranker uncertainty ± ${(post.uncertainty?.std ?? post.std).toFixed?.(2)} across ${post.uncertainty?.n_samples ?? post.n_samples ?? '?'} stochastic forward passes (MC-Dropout).`}
                                        className="inline-flex items-center px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 text-[10px] font-semibold border border-primary-100"
                                    >
                                        ± {(post.uncertainty?.std ?? post.std).toFixed(2)}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* More Menu */}
                    <Menu as="div" className="relative">
                        <Menu.Button className="p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">
                            <EllipsisHorizontalIcon className="w-5 h-5" />
                        </Menu.Button>
                        <Transition
                            as={Fragment}
                            enter="transition ease-out duration-100"
                            enterFrom="transform opacity-0 scale-95"
                            enterTo="transform opacity-100 scale-100"
                            leave="transition ease-in duration-75"
                            leaveFrom="transform opacity-100 scale-100"
                            leaveTo="transform opacity-0 scale-95"
                        >
                            <Menu.Items className="absolute right-0 mt-1 w-40 origin-top-right rounded-xl bg-white shadow-lg border border-neutral-100 focus:outline-none overflow-hidden z-10">
                                <Menu.Item>
                                    {({ active }) => (
                                        <button
                                            onClick={() => onReport?.(post.id)}
                                            className={cn(
                                                'w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left text-crisis-600',
                                                active && 'bg-crisis-50'
                                            )}
                                        >
                                            <FlagIcon className="w-4 h-4" />
                                            Report
                                        </button>
                                    )}
                                </Menu.Item>
                            </Menu.Items>
                        </Transition>
                    </Menu>
                </div>

                {/* Content */}
                <p className="text-neutral-700 whitespace-pre-wrap mb-4">{post.content}</p>

                {/* Reaction Chips (inline below content) */}
                <ReactionChips
                    reactions={localReactions}
                    myReactions={localMyReactions}
                    onReact={handleReact}
                />

                {/* Actions Bar */}
                <div className="flex items-center gap-1 pt-3 border-t border-neutral-100">
                    {/* Reaction Picker (replaces simple like) */}
                    <ReactionPicker
                        onReact={handleReact}
                        myReactions={localMyReactions}
                        disabled={!user?.id}
                    />

                    {/* Total reactions count */}
                    {totalReactions > 0 && (
                        <span className="text-xs text-neutral-400 font-medium mr-1">
                            {totalReactions}
                        </span>
                    )}

                    <button
                        onClick={handleToggleComments}
                        className={cn(
                            'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors',
                            showComments
                                ? 'text-primary-600 bg-primary-50'
                                : 'text-neutral-600 hover:bg-neutral-50'
                        )}
                    >
                        <ChatBubbleLeftIcon className="w-5 h-5" />
                        <span className="text-sm font-medium">{totalComments}</span>
                    </button>

                    <button
                        onClick={() => onShare?.(post.id)}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-neutral-600 hover:bg-neutral-50 transition-colors ml-auto"
                    >
                        <ShareIcon className="w-5 h-5" />
                    </button>
                </div>

                {/* Comments Section */}
                {/* Comments Section */}
                {showComments && (
                    <div className="mt-4 pt-4 border-t border-neutral-100 space-y-3">
                        {post.comments > 0 && localComments.length === 0 && (
                            <p className="text-xs text-neutral-400 text-center">
                                {post.comments} previous comment{post.comments !== 1 ? 's' : ''}
                            </p>
                        )}

                        {localComments.map((c) => (
                            <div key={c.id} className="flex items-start gap-2">
                                <Avatar firstName={c.author} size="sm" />
                                <div className="flex-1 bg-neutral-50 rounded-xl px-3 py-2">
                                    <p className="text-xs font-medium text-neutral-700 mb-0.5">{c.author}</p>
                                    <p className="text-sm text-neutral-600">{c.text}</p>
                                </div>
                            </div>
                        ))}

                        <div className="flex items-center gap-2">
                            <Avatar
                                firstName={user?.firstName || user?.guest_name || 'Y'}
                                size="sm"
                            />
                            <div className="flex-1 flex items-center gap-2 bg-neutral-50 border border-neutral-200 rounded-xl px-3 py-2 focus-within:border-primary-300 transition-colors">
                                <input
                                    type="text"
                                    value={commentInput}
                                    onChange={(e) => setCommentInput(e.target.value)}
                                    onKeyDown={handleCommentKeyDown}
                                    placeholder="Write a comment..."
                                    className="flex-1 bg-transparent text-sm text-neutral-700 placeholder-neutral-400 outline-none"
                                />
                                <button
                                    onClick={handleAddComment}
                                    disabled={!commentInput.trim()}
                                    className="text-primary-500 hover:text-primary-700 disabled:text-neutral-300 transition-colors"
                                >
                                    <PaperAirplaneIcon className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CommunityPost;

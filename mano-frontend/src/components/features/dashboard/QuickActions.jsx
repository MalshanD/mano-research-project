import { Link } from 'react-router-dom';
import { cn } from '../../../utils/helpers';
import {
    ChatBubbleLeftRightIcon,
    ClipboardDocumentListIcon,
    ChartBarIcon,
    UserGroupIcon,
    SparklesIcon,
    HeartIcon,
} from '@heroicons/react/24/outline';

const actions = [
    {
        name: 'Chat with Manō',
        description: 'Talk to our AI companion',
        href: '/chat',
        icon: ChatBubbleLeftRightIcon,
        emoji: '\uD83D\uDCAC',
        color: 'bg-terracotta',
        bgLight: 'bg-peach/30',
    },
    {
        name: 'Take Assessment',
        description: 'Check your mental health',
        href: '/assessments',
        icon: ClipboardDocumentListIcon,
        emoji: '\uD83D\uDCCB',
        color: 'bg-terracotta-light',
        bgLight: 'bg-cream',
    },
    {
        name: 'View Insights',
        description: 'See your predictions',
        href: '/predictions',
        icon: ChartBarIcon,
        emoji: '\uD83D\uDD2E',
        color: 'bg-lavender',
        bgLight: 'bg-blush/40',
    },
    {
        name: 'Community',
        description: 'Connect with peers',
        href: '/community',
        icon: UserGroupIcon,
        emoji: '\uD83E\uDDD1\u200D\uD83E\uDD1D\u200D\uD83E\uDDD1',
        color: 'bg-sage',
        bgLight: 'bg-mint/40',
    },
    {
        name: 'Activities',
        description: 'Wellness exercises',
        href: '/activities',
        icon: SparklesIcon,
        emoji: '\u2728',
        color: 'bg-sky',
        bgLight: 'bg-sky-light/20',
    },
    {
        name: 'Crisis Support',
        description: 'Get help now',
        href: '#crisis',
        icon: HeartIcon,
        emoji: '\u2764\uFE0F',
        color: 'bg-coral',
        bgLight: 'bg-coral-light/15',
        special: true,
    },
];

function QuickActions({ onCrisisClick, className }) {
    return (
        <div className={cn('grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4', className)}>
            {actions.map((action) => {
                const Icon = action.icon;
                const isLink = action.href !== '#crisis';

                const content = (
                    <div
                        className={cn(
                            'flex flex-col items-center p-4 rounded-3xl transition-all duration-200',
                            'hover:shadow-organic hover:-translate-y-1 cursor-pointer border border-transparent hover:border-sand/40',
                            action.bgLight
                        )}
                    >
                        <div
                            className={cn(
                                'w-12 h-12 rounded-2xl flex items-center justify-center mb-3',
                                action.color
                            )}
                        >
                            {action.emoji ? (
                                <span className="text-xl">{action.emoji}</span>
                            ) : (
                                <Icon className="w-6 h-6 text-white" />
                            )}
                        </div>
                        <h3 className="text-sm font-semibold text-neutral-900 text-center">
                            {action.name}
                        </h3>
                        <p className="text-xs text-neutral-500 text-center mt-0.5">
                            {action.description}
                        </p>
                    </div>
                );

                if (isLink) {
                    return (
                        <Link key={action.name} to={action.href}>
                            {content}
                        </Link>
                    );
                }

                return (
                    <div key={action.name} onClick={onCrisisClick}>
                        {content}
                    </div>
                );
            })}
        </div>
    );
}

export default QuickActions;
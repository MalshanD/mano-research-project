import { useState } from 'react';
import { cn } from '../../utils/helpers';
import { Badge } from './Badge';

function Tabs({
                  tabs,
                  defaultTab,
                  onChange,
                  variant = 'default', // default, pills, underline
                  orientation = 'horizontal', // horizontal, vertical
                  className,
              }) {
    const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

    const handleTabChange = (tabId) => {
        setActiveTab(tabId);
        onChange?.(tabId);
    };

    const activeTabContent = tabs.find((tab) => tab.id === activeTab)?.content;

    const baseTabClasses = 'flex items-center gap-2 font-medium transition-all whitespace-nowrap';

    const variantClasses = {
        default: {
            list: 'border-b border-neutral-200',
            tab: 'px-4 py-3 -mb-px border-b-2',
            active: 'border-primary-500 text-primary-600',
            inactive: 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300',
        },
        pills: {
            list: 'bg-neutral-100 p-1 rounded-xl',
            tab: 'px-4 py-2 rounded-lg',
            active: 'bg-white text-neutral-900 shadow-sm',
            inactive: 'text-neutral-600 hover:text-neutral-900',
        },
        underline: {
            list: '',
            tab: 'px-4 py-2 border-b-2',
            active: 'border-primary-500 text-primary-600',
            inactive: 'border-transparent text-neutral-500 hover:text-neutral-700',
        },
    };

    const classes = variantClasses[variant];

    if (orientation === 'vertical') {
        return (
            <div className={cn('flex flex-col lg:flex-row gap-6', className)}>
                {/* Tab List - Sidebar */}
                <div className="lg:w-64 flex-shrink-0">
                    <div className="sticky top-24">
                        <nav className="space-y-1">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => handleTabChange(tab.id)}
                                    className={cn(
                                        'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left font-medium transition-all',
                                        activeTab === tab.id
                                            ? 'bg-primary-50 text-primary-700'
                                            : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                                    )}
                                >
                                    {tab.icon && (
                                        <span className={cn(
                                            activeTab === tab.id ? 'text-primary-600' : 'text-neutral-400'
                                        )}>
                      {tab.icon}
                    </span>
                                    )}
                                    <span className="flex-1">{tab.label}</span>
                                    {tab.badge && (
                                        <Badge variant={activeTab === tab.id ? 'primary' : 'secondary'} size="sm">
                                            {tab.badge}
                                        </Badge>
                                    )}
                                </button>
                            ))}
                        </nav>
                    </div>
                </div>

                {/* Tab Content */}
                <div className="flex-1 min-w-0">
                    {activeTabContent}
                </div>
            </div>
        );
    }

    return (
        <div className={className}>
            {/* Tab List */}
            <div className={cn('flex overflow-x-auto scrollbar-hide', classes.list)}>
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
                        className={cn(
                            baseTabClasses,
                            classes.tab,
                            activeTab === tab.id ? classes.active : classes.inactive
                        )}
                    >
                        {tab.icon}
                        {tab.label}
                        {tab.badge && (
                            <Badge
                                variant={activeTab === tab.id ? 'primary' : 'secondary'}
                                size="sm"
                            >
                                {tab.badge}
                            </Badge>
                        )}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="mt-6">
                {activeTabContent}
            </div>
        </div>
    );
}

export default Tabs;
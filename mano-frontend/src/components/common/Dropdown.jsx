import { Fragment } from 'react';
import { Menu, Transition } from '@headlessui/react';
import { cn } from '../../utils/helpers';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

function Dropdown({
                      trigger,
                      items,
                      align = 'right',
                      className,
                  }) {
    const alignments = {
        left: 'left-0',
        right: 'right-0',
        center: 'left-1/2 -translate-x-1/2',
    };

    return (
        <Menu as="div" className={cn('relative inline-block text-left', className)}>
            <Menu.Button as={Fragment}>
                {trigger || (
                    <button className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-200 rounded-xl hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
                        Options
                        <ChevronDownIcon className="w-4 h-4" />
                    </button>
                )}
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
                <Menu.Items
                    className={cn(
                        'absolute z-50 mt-2 w-56 origin-top-right rounded-xl bg-white shadow-lg border border-neutral-100 focus:outline-none overflow-hidden',
                        alignments[align]
                    )}
                >
                    <div className="py-1">
                        {items.map((item, index) => {
                            if (item.type === 'divider') {
                                return <div key={index} className="my-1 border-t border-neutral-100" />;
                            }

                            if (item.type === 'header') {
                                return (
                                    <div key={index} className="px-4 py-2 text-xs font-semibold text-neutral-400 uppercase">
                                        {item.label}
                                    </div>
                                );
                            }

                            return (
                                <Menu.Item key={index} disabled={item.disabled}>
                                    {({ active }) => (
                                        <button
                                            onClick={item.onClick}
                                            className={cn(
                                                'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors',
                                                active ? 'bg-neutral-50 text-neutral-900' : 'text-neutral-700',
                                                item.danger && 'text-crisis-600 hover:bg-crisis-50',
                                                item.disabled && 'opacity-50 cursor-not-allowed'
                                            )}
                                        >
                                            {item.icon && (
                                                <span className={cn('w-5 h-5', item.danger ? 'text-crisis-500' : 'text-neutral-400')}>
                          {item.icon}
                        </span>
                                            )}
                                            <span className="flex-1">{item.label}</span>
                                            {item.shortcut && (
                                                <span className="text-xs text-neutral-400">{item.shortcut}</span>
                                            )}
                                        </button>
                                    )}
                                </Menu.Item>
                            );
                        })}
                    </div>
                </Menu.Items>
            </Transition>
        </Menu>
    );
}

export default Dropdown;
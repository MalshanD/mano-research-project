import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import logoImg from '../../../assets/images/logo.png';
import {
    EllipsisVerticalIcon,
    PhoneIcon,
    InformationCircleIcon,
    TrashIcon,
    ArrowLeftIcon,
} from '@heroicons/react/24/outline';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import PersonaSelector from './PersonaSelector';

function ChatHeader({
    title = 'Manō',
    subtitle = 'AI Companion',
    status = 'online',
    persona,
    onPersonaChange,
    onBack,
    onInfo,
    onClear,
    onCrisis,
    showBackButton = false,
    className,
}) {
    const statusColors = {
        online: 'bg-success-500',
        offline: 'bg-neutral-400',
        busy: 'bg-warning-500',
    };

    // Avatar gradient follows active persona color
    const avatarGradient = persona
        ? `bg-gradient-to-br ${persona.color}`
        : 'bg-gradient-to-br from-primary-500 to-primary-600';

    return (
        <div
            className={cn(
                'flex items-center justify-between px-4 py-3 bg-white border-b border-neutral-100',
                className
            )}
        >
            <div className="flex items-center gap-3">
                {/* Back Button (Mobile) */}
                {showBackButton && (
                    <button
                        onClick={onBack}
                        className="p-2 -ml-2 text-neutral-600 hover:bg-neutral-100 rounded-lg lg:hidden"
                    >
                        <ArrowLeftIcon className="w-5 h-5" />
                    </button>
                )}

                {/* Avatar — morphs with persona */}
                <div className="relative">
                    <div className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300',
                        avatarGradient
                    )}>
                        {persona ? (
                            <span className="text-lg">{persona.emoji}</span>
                        ) : (
                            <img src={logoImg} alt="Manō" className="w-full h-full rounded-full object-cover" />
                        )}
                    </div>
                    <span
                        className={cn(
                            'absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white',
                            statusColors[status]
                        )}
                    />
                </div>

                {/* Title + active persona label */}
                <div>
                    <h2 className="font-semibold text-neutral-900 leading-tight">{title}</h2>
                    <p className="text-xs text-neutral-400 leading-tight">
                        {persona ? `${persona.label} mode` : subtitle}
                    </p>
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1.5">
                {/* ── Persona Selector ── */}
                {persona && onPersonaChange && (
                    <PersonaSelector persona={persona} onSelect={onPersonaChange} />
                )}

                {/* Crisis Button */}
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onCrisis}
                    className="text-crisis-600 hover:bg-crisis-50"
                >
                    <PhoneIcon className="w-4 h-4 mr-1" />
                    <span className="hidden sm:inline">Crisis Help</span>
                </Button>

                {/* More Menu */}
                <Menu as="div" className="relative">
                    <Menu.Button className="p-2 text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">
                        <EllipsisVerticalIcon className="w-5 h-5" />
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
                        <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-xl bg-white shadow-lg border border-neutral-100 focus:outline-none overflow-hidden z-10">
                            <div className="py-1">
                                <Menu.Item>
                                    {({ active }) => (
                                        <button
                                            onClick={onInfo}
                                            className={cn(
                                                'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left',
                                                active ? 'bg-neutral-50' : ''
                                            )}
                                        >
                                            <InformationCircleIcon className="w-5 h-5 text-neutral-400" />
                                            Chat Info
                                        </button>
                                    )}
                                </Menu.Item>
                                <Menu.Item>
                                    {({ active }) => (
                                        <button
                                            onClick={onClear}
                                            className={cn(
                                                'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left text-crisis-600',
                                                active ? 'bg-crisis-50' : ''
                                            )}
                                        >
                                            <TrashIcon className="w-5 h-5" />
                                            Clear Chat
                                        </button>
                                    )}
                                </Menu.Item>
                            </div>
                        </Menu.Items>
                    </Transition>
                </Menu>
            </div>
        </div>
    );
}

export default ChatHeader;
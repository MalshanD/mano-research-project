import { useState, useRef, useEffect } from 'react';
import { cn } from '../../../utils/helpers';
import { ChevronDownIcon, CheckIcon } from '@heroicons/react/24/outline';

export const PERSONAS = [
    {
        id: 'friend',
        label: 'Friend',
        emoji: '🤝',
        color: 'from-sky-400 to-cyan-500',
        ring: 'ring-sky-300',
        pill: 'bg-sky-50 text-sky-700 border-sky-200',
        dot: 'bg-sky-400',
        description: 'Casual, warm & empathetic',
    },
    {
        id: 'counselor',
        label: 'Counselor',
        emoji: '🧠',
        color: 'from-violet-500 to-purple-600',
        ring: 'ring-violet-300',
        pill: 'bg-violet-50 text-violet-700 border-violet-200',
        dot: 'bg-violet-400',
        description: 'Reflective & professionally supportive',
    },
    {
        id: 'medical_officer',
        label: 'Medical Officer',
        emoji: '🩺',
        color: 'from-emerald-500 to-teal-600',
        ring: 'ring-emerald-300',
        pill: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        dot: 'bg-emerald-400',
        description: 'Clinical, precise & informative',
    },
];

export function usePersona() {
    const [persona, setPersona] = useState(PERSONAS[0]); // default: Friend
    return { persona, setPersona };
}

function PersonaSelector({ persona, onSelect, className }) {
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div ref={ref} className={cn('relative', className)}>
            {/* Current Persona Pill — toggle button */}
            <button
                onClick={() => setOpen((o) => !o)}
                className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border text-xs font-semibold',
                    'transition-all duration-200 hover:shadow-sm',
                    persona.pill
                )}
            >
                <span>{persona.emoji}</span>
                <span className="hidden sm:inline">{persona.label}</span>
                <ChevronDownIcon
                    className={cn('w-3 h-3 transition-transform duration-200', open && 'rotate-180')}
                />
            </button>

            {/* Dropdown */}
            {open && (
                <div className={cn(
                    'absolute right-0 top-full mt-2 z-50',
                    'w-64 bg-white rounded-2xl shadow-xl border border-neutral-100',
                    'overflow-hidden animate-fade-in-down'
                )}>
                    {/* Header */}
                    <div className="px-4 pt-3 pb-2 border-b border-neutral-50">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">
                            Switch Persona
                        </p>
                    </div>

                    <div className="p-2 space-y-1">
                        {PERSONAS.map((p) => {
                            const isActive = p.id === persona.id;
                            return (
                                <button
                                    key={p.id}
                                    onClick={() => { onSelect(p); setOpen(false); }}
                                    className={cn(
                                        'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150',
                                        isActive
                                            ? 'bg-neutral-50 ring-1 ring-neutral-200'
                                            : 'hover:bg-neutral-50'
                                    )}
                                >
                                    {/* Avatar circle */}
                                    <div className={cn(
                                        'w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center',
                                        'bg-gradient-to-br text-lg shadow-sm',
                                        p.color
                                    )}>
                                        {p.emoji}
                                    </div>

                                    {/* Labels */}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-neutral-900 leading-tight">
                                            {p.label}
                                        </p>
                                        <p className="text-xs text-neutral-400 truncate">
                                            {p.description}
                                        </p>
                                    </div>

                                    {/* Active check */}
                                    {isActive && (
                                        <CheckIcon className="w-4 h-4 text-primary-500 flex-shrink-0" />
                                    )}
                                </button>
                            );
                        })}
                    </div>

                    <div className="px-4 py-2.5 border-t border-neutral-50 bg-neutral-50/50">
                        <p className="text-[10px] text-neutral-400 leading-snug">
                            Persona shapes how Manō responds. You can switch anytime.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

export default PersonaSelector;

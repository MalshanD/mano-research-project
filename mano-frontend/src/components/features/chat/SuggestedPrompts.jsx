import { cn } from '../../../utils/helpers';
import {
    ChatBubbleLeftRightIcon,
    HeartIcon,
    SparklesIcon,
    LightBulbIcon,
    FaceSmileIcon,
    MoonIcon,
    HandRaisedIcon,
    ShieldExclamationIcon,
    ClipboardDocumentListIcon,
    BeakerIcon,
    ExclamationTriangleIcon,
    ArrowPathIcon,
} from '@heroicons/react/24/outline';

const PERSONA_PROMPTS = {
    friend: [
        { icon: HeartIcon,                   text: "I'm feeling really down today" },
        { icon: ChatBubbleLeftRightIcon,      text: "Can we just chat for a bit?" },
        { icon: HandRaisedIcon,              text: "I need someone to listen to me" },
        { icon: SparklesIcon,                text: "Help me with a breathing exercise" },
        { icon: FaceSmileIcon,               text: "Share something to cheer me up" },
        { icon: MoonIcon,                    text: "I'm feeling overwhelmed right now" },
    ],
    counselor: [
        { icon: HeartIcon,                   text: "I've been feeling anxious recently" },
        { icon: LightBulbIcon,               text: "Help me understand my emotions" },
        { icon: ArrowPathIcon,               text: "I need coping strategies for stress" },
        { icon: ChatBubbleLeftRightIcon,     text: "Let's explore how I'm feeling" },
        { icon: MoonIcon,                    text: "I've been having trouble sleeping" },
        { icon: SparklesIcon,               text: "I'm struggling with negative thoughts" },
    ],
    medical_officer: [
        { icon: ClipboardDocumentListIcon,   text: "What are common signs of depression?" },
        { icon: BeakerIcon,                  text: "How does anxiety affect the body?" },
        { icon: ShieldExclamationIcon,       text: "I've been experiencing panic attacks" },
        { icon: LightBulbIcon,              text: "What breathing techniques help stress?" },
        { icon: ExclamationTriangleIcon,    text: "When should I seek professional help?" },
        { icon: MoonIcon,                   text: "I have recurring fatigue and headaches" },
    ],
};

const PERSONA_META = {
    friend: {
        hint: 'Not sure where to start? Try one of these:',
        hoverBorder: 'hover:border-sky-200',
        hoverBg: 'hover:bg-sky-50',
        iconHoverBg: 'group-hover:bg-sky-100',
        iconHoverText: 'group-hover:text-sky-600',
        textHover: 'group-hover:text-sky-700',
    },
    counselor: {
        hint: 'What would you like to explore today?',
        hoverBorder: 'hover:border-violet-200',
        hoverBg: 'hover:bg-violet-50',
        iconHoverBg: 'group-hover:bg-violet-100',
        iconHoverText: 'group-hover:text-violet-600',
        textHover: 'group-hover:text-violet-700',
    },
    medical_officer: {
        hint: 'Select a topic to discuss with your Medical Officer:',
        hoverBorder: 'hover:border-emerald-200',
        hoverBg: 'hover:bg-emerald-50',
        iconHoverBg: 'group-hover:bg-emerald-100',
        iconHoverText: 'group-hover:text-emerald-600',
        textHover: 'group-hover:text-emerald-700',
    },
};

function SuggestedPrompts({ persona, onSelect, className }) {
    const personaId = persona?.id || 'friend';
    const prompts = PERSONA_PROMPTS[personaId] ?? PERSONA_PROMPTS.friend;
    const meta = PERSONA_META[personaId] ?? PERSONA_META.friend;

    return (
        <div className={cn('p-4', className)}>
            <p className="text-sm text-neutral-500 mb-3 text-center">
                {meta.hint}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {prompts.map((prompt, index) => {
                    const Icon = prompt.icon;
                    return (
                        <button
                            key={index}
                            onClick={() => onSelect(prompt.text)}
                            className={cn(
                                'flex items-center gap-3 p-3 bg-white rounded-xl border border-neutral-100',
                                'transition-all text-left group',
                                meta.hoverBorder,
                                meta.hoverBg
                            )}
                        >
                            <div className={cn(
                                'w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center transition-colors flex-shrink-0',
                                meta.iconHoverBg
                            )}>
                                <Icon className={cn('w-4 h-4 text-neutral-500 transition-colors', meta.iconHoverText)} />
                            </div>
                            <span className={cn('text-sm text-neutral-700 transition-colors', meta.textHover)}>
                                {prompt.text}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default SuggestedPrompts;
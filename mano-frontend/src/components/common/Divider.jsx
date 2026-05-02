import { cn } from '../../utils/helpers';

function Divider({
                     orientation = 'horizontal',
                     label,
                     className
                 }) {
    if (orientation === 'vertical') {
        return (
            <div
                className={cn('w-px bg-neutral-200 self-stretch', className)}
                role="separator"
                aria-orientation="vertical"
            />
        );
    }

    if (label) {
        return (
            <div className={cn('flex items-center', className)}>
                <div className="flex-1 border-t border-neutral-200" />
                <span className="px-4 text-sm text-neutral-500">{label}</span>
                <div className="flex-1 border-t border-neutral-200" />
            </div>
        );
    }

    return (
        <hr
            className={cn('border-t border-neutral-200', className)}
            role="separator"
            aria-orientation="horizontal"
        />
    );
}

export default Divider;
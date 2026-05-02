import { cn } from '../../utils/helpers';
import Button from './Button';

function EmptyState({
                        icon,
                        title,
                        description,
                        action,
                        actionLabel,
                        onAction,
                        className,
                    }) {
    return (
        <div
            className={cn(
                'flex flex-col items-center justify-center py-12 px-4 text-center',
                className
            )}
        >
            {icon && (
                <div className="w-16 h-16 mb-4 rounded-2xl bg-neutral-100 flex items-center justify-center text-neutral-400">
                    {icon}
                </div>
            )}
            {title && (
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">{title}</h3>
            )}
            {description && (
                <p className="text-neutral-500 max-w-sm mb-6">{description}</p>
            )}
            {(action || (actionLabel && onAction)) && (
                action || (
                    <Button onClick={onAction} variant="primary">
                        {actionLabel}
                    </Button>
                )
            )}
        </div>
    );
}

export default EmptyState;
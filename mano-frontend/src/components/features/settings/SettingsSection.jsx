import { cn } from '../../../utils/helpers';
import { Card } from '../../common';

function SettingsSection({
                             title,
                             description,
                             icon,
                             children,
                             className,
                         }) {
    const Icon = icon;

    return (
        <Card className={cn('', className)}>
            <div className="flex items-start gap-4 mb-6">
                {Icon && (
                    <div className="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-primary-600" />
                    </div>
                )}
                <div>
                    <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
                    {description && (
                        <p className="text-sm text-neutral-500 mt-1">{description}</p>
                    )}
                </div>
            </div>
            {children}
        </Card>
    );
}

export default SettingsSection;
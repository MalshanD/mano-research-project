import { cn } from '../../utils/helpers';

function PageContainer({
                           children,
                           title,
                           subtitle,
                           actions,
                           breadcrumbs,
                           maxWidth = '7xl',
                           className,
                       }) {
    const maxWidths = {
        sm: 'max-w-screen-sm',
        md: 'max-w-screen-md',
        lg: 'max-w-screen-lg',
        xl: 'max-w-screen-xl',
        '2xl': 'max-w-screen-2xl',
        '7xl': 'max-w-7xl',
        full: 'max-w-full',
    };

    return (
        <div className={cn('mx-auto', maxWidths[maxWidth], className)}>
            {/* Breadcrumbs */}
            {breadcrumbs && (
                <nav className="mb-4" aria-label="Breadcrumb">
                    <ol className="flex items-center space-x-2 text-sm">
                        {breadcrumbs.map((crumb, index) => (
                            <li key={index} className="flex items-center">
                                {index > 0 && (
                                    <svg
                                        className="w-4 h-4 text-neutral-400 mx-2"
                                        fill="currentColor"
                                        viewBox="0 0 20 20"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                                            clipRule="evenodd"
                                        />
                                    </svg>
                                )}
                                {crumb.href ? (
                                    <a href={crumb.href}
                                    className="text-neutral-500 hover:text-neutral-700 transition-colors">
                                        {crumb.label}
                                    </a>
                                    ) : (
                                    <span className="text-neutral-900 font-medium">{crumb.label}</span>
                        )}
                    </li>
                    ))}
                </ol>
                </nav>
                )}

{/* Page Header */}
{(title || actions) && (
    <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
            {title && (
                <h1 className="text-2xl lg:text-3xl font-bold font-display text-neutral-900">
                    {title}
                </h1>
            )}
            {subtitle && (
                <p className="mt-1 text-neutral-500">{subtitle}</p>
            )}
        </div>
        {actions && (
            <div className="flex items-center gap-3">
                {actions}
            </div>
        )}
    </div>
)}

{/* Page Content */}
{children}
</div>
);
}

export default PageContainer;
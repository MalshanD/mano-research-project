/**
 * SeverityChip — renders a colour + icon + text badge from a backend
 * RenderHint payload ({ severity_color, icon_hint, microcopy }).
 *
 * Accessibility: the colour is always paired with an icon and text;
 * the chip carries an aria-label tone prefix so screen readers get the
 * severity context without reading the icon's alt text.
 */

import { iconFor, classesFor, ariaLabelFor } from '../../lib/c1/severityTokens';
import clsx from 'clsx';

export default function SeverityChip({ render, size = 'md', children, className }) {
    if (!render) return null;
    const Icon = iconFor(render.icon_hint);
    const classes = classesFor(render.severity_color);
    const aria = ariaLabelFor(render.severity_color, render.microcopy || '');

    const sizeClasses =
        size === 'sm' ? 'px-2 py-0.5 text-xs gap-1'
        : size === 'lg' ? 'px-4 py-2 text-base gap-2'
        : 'px-3 py-1 text-sm gap-1.5';

    return (
        <span
            role="status"
            aria-label={aria}
            className={clsx(
                'inline-flex items-center rounded-full font-medium',
                classes.chip,
                sizeClasses,
                className,
            )}
        >
            <Icon aria-hidden="true" className="w-4 h-4" />
            <span>{children ?? render.microcopy}</span>
        </span>
    );
}

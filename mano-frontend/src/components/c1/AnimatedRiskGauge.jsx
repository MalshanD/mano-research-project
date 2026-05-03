/**
 * AnimatedRiskGauge — circular gauge that sweeps from 0 to the target
 * risk probability and counts up the percentage label.
 *
 * Honours `prefers-reduced-motion`. Always pairs the colour with an
 * icon + text label so colour-vision-impaired users get the same
 * signal.
 */

import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { iconFor, classesFor, riskLabelFor } from '../../lib/c1/severityTokens';

export default function AnimatedRiskGauge({
    riskLevel,           // "Low" | "Medium" | "High"
    confidence,          // 0..1
    severityColor,       // e.g. "emerald-500"
    iconHint,            // e.g. "shield-check"
    sublabel,            // optional small caption under the gauge
}) {
    const reduce = useReducedMotion();
    const Icon = iconFor(iconHint);
    const classes = classesFor(severityColor);

    const [displayPct, setDisplayPct] = useState(0);
    const targetPct = typeof confidence === 'number' && !isNaN(confidence)
        ? Math.round(confidence * 100)
        : 0;

    useEffect(() => {
        if (reduce) {
            setDisplayPct(targetPct);
            return;
        }
        let raf;
        const start = performance.now();
        const duration = 800;
        const tick = (now) => {
            const elapsed = now - start;
            const t = Math.min(1, elapsed / duration);
            // Ease-out-cubic.
            const eased = 1 - Math.pow(1 - t, 3);
            setDisplayPct(Math.round(targetPct * eased));
            if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [targetPct, reduce]);

    // Geometry — donut radius 60, stroke 14.
    const r = 60;
    const c = 2 * Math.PI * r;
    const offset = c * (1 - displayPct / 100);

    const ariaLabel = `${riskLabelFor(riskLevel)}, ${targetPct}% confidence.`;

    return (
        <figure
            role="img"
            aria-label={ariaLabel}
            className="flex flex-col items-center"
        >
            <svg viewBox="0 0 160 160" className="w-40 h-40">
                {/* Track */}
                <circle
                    cx="80" cy="80" r={r}
                    fill="none" strokeWidth="14"
                    className="stroke-slate-200 dark:stroke-slate-800"
                />
                {/* Sweep */}
                <motion.circle
                    cx="80" cy="80" r={r}
                    fill="none" strokeWidth="14"
                    strokeLinecap="round"
                    transform="rotate(-90 80 80)"
                    strokeDasharray={c}
                    strokeDashoffset={offset}
                    className={classes.text}
                    style={{ stroke: 'currentColor' }}
                />
                {/* Center icon + percentage */}
                <foreignObject x="40" y="50" width="80" height="60">
                    <div xmlns="http://www.w3.org/1999/xhtml" className="flex flex-col items-center justify-center text-center">
                        <Icon aria-hidden="true" className={`w-6 h-6 ${classes.text}`} />
                        <span className={`mt-1 text-2xl font-semibold ${classes.text}`}>
                            {displayPct}%
                        </span>
                    </div>
                </foreignObject>
            </svg>
            <figcaption className="mt-1 text-sm text-slate-600 dark:text-slate-400 text-center">
                <span className="font-medium">{riskLabelFor(riskLevel)}</span>
                {sublabel ? <span className="block text-xs opacity-70">{sublabel}</span> : null}
            </figcaption>
        </figure>
    );
}

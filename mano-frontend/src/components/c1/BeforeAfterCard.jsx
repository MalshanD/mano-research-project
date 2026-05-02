/**
 * BeforeAfterCard — Seq2Seq simulation outcome rendered as a paired
 * "today vs. day-7" card. Uses two SeverityChips and a delta arrow.
 *
 * UX guideline: the delta is the headline. Numbers are secondary.
 */

import { iconFor, classesFor, riskLabelFor } from '../../lib/c1/severityTokens';
import { ArrowRight } from 'lucide-react';

function Side({ title, riskLevel, highProb, render }) {
    const Icon = iconFor(render?.icon_hint);
    const classes = classesFor(render?.severity_color);
    return (
        <div className="flex-1 min-w-0">
            <p className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {title}
            </p>
            <div className={`mt-2 flex items-center gap-2 rounded-lg border px-3 py-2 ${classes.border} ${classes.bg}`}>
                <Icon aria-hidden="true" className={`w-5 h-5 shrink-0 ${classes.text}`} />
                <div className="min-w-0">
                    <p className={`text-sm font-medium ${classes.text}`}>
                        {riskLabelFor(riskLevel)}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                        {Math.round(highProb * 100)}% high-risk probability
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function BeforeAfterCard({
    title,                // "Continue current plan" | "CBT" | …
    beforeRiskLevel,
    beforeHighProb,
    beforeRender,
    afterRiskLevel,
    afterHighProb,
    afterRender,
    deltaRender,          // RenderHint — emerald (improvement), rose (worsening), amber (flat)
    narrative,            // short Day-7 reflection
    onTryThisPlan,        // callback fired when the user clicks "Try this plan"
}) {
    return (
        <article className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-sm hover:shadow-md transition-shadow">
            <header className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
                        {title}
                    </h3>
                </div>
            </header>

            <div className="mt-4 flex items-stretch gap-3">
                <Side
                    title="Right now"
                    riskLevel={beforeRiskLevel}
                    highProb={beforeHighProb}
                    render={beforeRender}
                />
                <div className="flex flex-col items-center justify-center px-1 text-slate-400">
                    <ArrowRight aria-hidden="true" className="w-5 h-5" />
                    <span className="sr-only">Projects to</span>
                </div>
                <Side
                    title="In 7 days"
                    riskLevel={afterRiskLevel}
                    highProb={afterHighProb}
                    render={afterRender}
                />
            </div>

            {narrative ? (
                <blockquote className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-sm italic text-slate-700 dark:text-slate-300">
                    &ldquo;{narrative}&rdquo;
                </blockquote>
            ) : null}

            {onTryThisPlan ? (
                <footer className="mt-4">
                    <button
                        type="button"
                        onClick={onTryThisPlan}
                        className="w-full rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-4 py-2.5 text-sm font-medium hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-900"
                    >
                        Try this plan
                    </button>
                </footer>
            ) : null}
        </article>
    );
}

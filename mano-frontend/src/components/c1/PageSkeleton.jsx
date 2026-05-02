/**
 * PageSkeleton — never show a blank white screen while a page bundle
 * is loading. Renders a header band, a hero card, and three card
 * placeholders that match the rhythm of the real page.
 */

export default function PageSkeleton({ withHero = true, cardCount = 3 }) {
    return (
        <div role="status" aria-label="Loading page" className="animate-pulse">
            <div className="h-7 w-1/3 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="mt-2 h-4 w-2/3 rounded bg-slate-100 dark:bg-slate-800/60" />
            {withHero && (
                <div className="mt-6 rounded-2xl bg-slate-100 dark:bg-slate-800/50 h-44 sm:h-56" />
            )}
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: cardCount }).map((_, i) => (
                    <div
                        key={i}
                        className="rounded-2xl bg-slate-100 dark:bg-slate-800/50 h-40"
                    />
                ))}
            </div>
            <span className="sr-only">Loading…</span>
        </div>
    );
}

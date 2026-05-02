/**
 * PatientStateGate — every C1 page wraps its body in this gate so the
 * loading / no_patient / incomplete / error states are handled
 * consistently.
 *
 * The user always sees something meaningful, never a blank page or a
 * silently-mocked result.
 */

import { Link } from 'react-router-dom';
import { iconFor } from '../../lib/c1/severityTokens';
import { UserPlus, AlertTriangle, RotateCw, Activity } from 'lucide-react';
import PageSkeleton from './PageSkeleton';

function CenteredCard({ icon: Icon, title, body, actions }) {
    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center max-w-xl mx-auto">
            <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center">
                <Icon aria-hidden="true" className="w-6 h-6 text-emerald-600" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{body}</p>
            {actions ? <div className="mt-5 flex justify-center gap-2">{actions}</div> : null}
        </div>
    );
}

export default function PatientStateGate({
    status, error, onRetry, children,
}) {
    if (status === 'loading') return <div className="mt-4"><PageSkeleton cardCount={3} /></div>;

    if (status === 'no_patient') {
        return (
            <CenteredCard
                icon={UserPlus}
                title="Create your patient profile first"
                body="Component 1's models need a baseline of who you are and seven days of vitals before they can predict, simulate, or recommend. Generate a Digital Twin or import a profile to get started."
                actions={
                    <Link
                        to="/c1/twin"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 text-sm font-medium"
                    >
                        Generate Digital Twin
                    </Link>
                }
            />
        );
    }

    if (status === 'incomplete') {
        return (
            <CenteredCard
                icon={Activity}
                title="We need 7 days of vitals to compute this"
                body="Your profile exists, but it doesn't have the seven-day vitals window the models require. Connect a wearable, log a week of journal entries, or regenerate your Digital Twin."
                actions={
                    <Link
                        to="/c1/twin"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 text-sm font-medium"
                    >
                        Regenerate Digital Twin
                    </Link>
                }
            />
        );
    }

    if (status === 'error') {
        return (
            <CenteredCard
                icon={AlertTriangle}
                title="Couldn't load your profile"
                body={String(error || 'The backend rejected the request.')}
                actions={
                    onRetry ? (
                        <button
                            type="button"
                            onClick={onRetry}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-2 text-sm font-medium"
                        >
                            <RotateCw aria-hidden="true" className="w-3.5 h-3.5" /> Try again
                        </button>
                    ) : null
                }
            />
        );
    }

    return children;
}

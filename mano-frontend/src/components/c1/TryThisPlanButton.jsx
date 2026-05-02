/**
 * TryThisPlanButton — a one-line component that turns a See-My-Future
 * scenario into a navigation to the AI Recommendation page with the
 * intervention pre-filled.
 */

import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';

export default function TryThisPlanButton({ interventionType, label = 'Try this plan' }) {
    const navigate = useNavigate();
    return (
        <button
            type="button"
            onClick={() => navigate(`/c1/recommendation?prefill=${interventionType}`)}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 text-sm font-semibold shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-emerald-500"
        >
            <Sparkles aria-hidden="true" className="w-4 h-4" />
            {label}
        </button>
    );
}

/**
 * JournalTrendChart — Recharts-based visualisation for CBT journal trends.
 *
 * Supports two modes:
 *  1. Severity over time  (daily_severity data)
 *  2. Distortion frequency (bar chart from distortion_frequency)
 */

import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    Cell,
} from 'recharts';
import { cn } from '../../utils/helpers';

// ─── Colour palette for distortion types ────────────────────────────────────
const DISTORTION_COLORS = {
    catastrophizing: '#ef4444',
    black_and_white: '#6366f1',
    overgeneralization: '#f59e0b',
    mind_reading: '#8b5cf6',
    fortune_telling: '#0ea5e9',
    emotional_reasoning: '#ec4899',
    should_statements: '#14b8a6',
    labeling: '#f97316',
    personalization: '#64748b',
    discounting_positive: '#a855f7',
    none: '#22c55e',
};

const BAR_FALLBACK_COLOR = '#6366f1';

// ─── Custom tooltip ─────────────────────────────────────────────────────────
function SeverityTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white rounded-xl shadow-lg border border-neutral-100 p-3 min-w-[160px]">
            <p className="text-xs font-semibold text-neutral-500 mb-1.5">{label}</p>
            {payload.map((entry, i) => (
                <div key={i} className="flex items-center justify-between gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span className="text-neutral-600">{entry.name}</span>
                    </div>
                    <span className="font-semibold text-neutral-900">{entry.value}</span>
                </div>
            ))}
        </div>
    );
}

function FreqTooltip({ active, payload }) {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
        <div className="bg-white rounded-xl shadow-lg border border-neutral-100 p-3 min-w-[140px]">
            <p className="text-xs font-semibold text-neutral-900 capitalize mb-1">{d.name}</p>
            <p className="text-sm text-neutral-600">
                Count: <span className="font-semibold text-neutral-900">{d.count}</span>
            </p>
        </div>
    );
}

// ─── Severity Area Chart ────────────────────────────────────────────────────
export function SeverityTrendChart({ data = [], height = 260, className }) {
    if (!data || data.length === 0) {
        return (
            <div className={cn('flex items-center justify-center bg-neutral-50 rounded-xl', className)} style={{ height }}>
                <p className="text-sm text-neutral-400">No severity data yet</p>
            </div>
        );
    }

    // Format date labels shorter
    const formatted = data.map((d) => ({
        ...d,
        label: new Date(d.date + 'T00:00:00').toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    }));

    return (
        <div className={cn('w-full', className)} style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formatted} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                    <XAxis
                        dataKey="label"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 11, fill: '#737373' }}
                        dy={10}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 11, fill: '#737373' }}
                        domain={[0, 3]}
                        ticks={[0, 1, 2, 3]}
                        dx={-10}
                    />
                    <Tooltip content={<SeverityTooltip />} />
                    <Legend verticalAlign="top" height={32} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '12px' }} />
                    <Area
                        type="monotone"
                        dataKey="avg_severity"
                        name="Avg Severity"
                        stroke="#f97316"
                        fill="#f97316"
                        fillOpacity={0.1}
                        strokeWidth={2}
                        dot={{ r: 3, strokeWidth: 2, fill: '#fff' }}
                        activeDot={{ r: 5, strokeWidth: 2, fill: '#fff' }}
                    />
                    <Area
                        type="monotone"
                        dataKey="entries"
                        name="Entries"
                        stroke="#6366f1"
                        fill="#6366f1"
                        fillOpacity={0.08}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

// ─── Distortion Frequency Bar Chart ─────────────────────────────────────────
export function DistortionBarChart({ frequencyMap = {}, height = 280, className }) {
    const data = Object.entries(frequencyMap)
        .map(([type, count]) => ({
            type,
            name: type.replace(/_/g, ' '),
            count,
            color: DISTORTION_COLORS[type] || BAR_FALLBACK_COLOR,
        }))
        .sort((a, b) => b.count - a.count);

    if (data.length === 0) {
        return (
            <div className={cn('flex items-center justify-center bg-neutral-50 rounded-xl', className)} style={{ height }}>
                <p className="text-sm text-neutral-400">No distortion data yet</p>
            </div>
        );
    }

    return (
        <div className={cn('w-full', className)} style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" horizontal={false} />
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#737373' }} />
                    <YAxis
                        type="category"
                        dataKey="name"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 11, fill: '#525252' }}
                        width={120}
                    />
                    <Tooltip content={<FreqTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
                    <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={18}>
                        {data.map((d, i) => (
                            <Cell key={i} fill={d.color} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

export default SeverityTrendChart;

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from 'recharts';
import { cn } from '../../utils/helpers';

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white rounded-xl shadow-lg border border-neutral-100 p-3">
                <p className="text-sm font-medium text-neutral-900 mb-2">{label}</p>
                {payload.map((entry, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: entry.color }}
                        />
                        <span className="text-neutral-600">{entry.name}:</span>
                        <span className="font-medium text-neutral-900">
              {(entry.value * 100).toFixed(0)}%
            </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

function TrendChart({
                        data = [],
                        lines = [
                            { key: 'stress', name: 'Stress', color: '#f97316' },
                            { key: 'depression', name: 'Depression', color: '#8b5cf6' },
                            { key: 'anxiety', name: 'Anxiety', color: '#0ea5e9' },
                        ],
                        height = 300,
                        showGrid = true,
                        showLegend = true,
                        className,
                    }) {
    if (!data || data.length === 0) {
        return (
            <div className={cn('flex items-center justify-center bg-neutral-50 rounded-xl', className)} style={{ height }}>
                <p className="text-neutral-400">No data available</p>
            </div>
        );
    }

    return (
        <div className={cn('w-full', className)} style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    {showGrid && (
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                    )}
                    <XAxis
                        dataKey="date"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 12, fill: '#737373' }}
                        dy={10}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 12, fill: '#737373' }}
                        tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                        domain={[0, 1]}
                        dx={-10}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    {showLegend && (
                        <Legend
                            verticalAlign="top"
                            height={36}
                            iconType="circle"
                            iconSize={8}
                            wrapperStyle={{ fontSize: '12px' }}
                        />
                    )}
                    {lines.map((line) => (
                        <Area
                            key={line.key}
                            type="monotone"
                            dataKey={line.key}
                            name={line.name}
                            stroke={line.color}
                            fill={line.color}
                            fillOpacity={0.1}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
                        />
                    ))}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

export default TrendChart;
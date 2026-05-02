import { cn } from '../../../utils/helpers';
import { Card, CardHeader, CardTitle, Badge, Button } from '../../common';
import { RiskGauge } from '../../charts';
import { ArrowRightIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';

function RiskOverview({
                          stressScore = 0,
                          depressionScore = 0,
                          anxietyScore = 0,
                          overallRisk = 'LOW',
                          lastUpdated,
                          loading = false,
                          className,
                      }) {
    const getRiskConfig = (level) => {
        const configs = {
            LOW: { color: 'success', label: 'Low Risk', message: 'You\'re doing well! Keep up the good work.' },
            MEDIUM: { color: 'warning', label: 'Medium Risk', message: 'Some areas need attention. Consider taking an assessment.' },
            HIGH: { color: 'accent', label: 'High Risk', message: 'We recommend speaking with a professional.' },
            SEVERE: { color: 'danger', label: 'Severe Risk', message: 'Please reach out for support. We\'re here for you.' },
            CRITICAL: { color: 'danger', label: 'Critical', message: 'Immediate support is recommended.' },
        };
        return configs[level] || configs.LOW;
    };

    const riskConfig = getRiskConfig(overallRisk);

    if (loading) {
        return (
            <Card className={cn('', className)}>
                <div className="animate-pulse">
                    <div className="h-6 bg-neutral-200 rounded w-1/3 mb-6" />
                    <div className="flex justify-around mb-6">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="flex flex-col items-center">
                                <div className="w-24 h-16 bg-neutral-200 rounded-full mb-2" />
                                <div className="h-4 bg-neutral-200 rounded w-16" />
                            </div>
                        ))}
                    </div>
                    <div className="h-16 bg-neutral-200 rounded" />
                </div>
            </Card>
        );
    }

    return (
        <Card className={cn('', className)}>
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                    <span>{'\uD83E\uDDE0'}</span> Mental Health Overview
                </CardTitle>
                <Badge variant={riskConfig.color} dot>
                    {riskConfig.label}
                </Badge>
            </CardHeader>

            {/* Risk Gauges */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <RiskGauge
                    value={stressScore}
                    label="Stress"
                    size="sm"
                />
                <RiskGauge
                    value={depressionScore}
                    label="Depression"
                    size="sm"
                />
                <RiskGauge
                    value={anxietyScore}
                    label="Anxiety"
                    size="sm"
                />
            </div>

            {/* Risk Message */}
            <div
                className={cn(
                    'p-4 rounded-2xl mb-4',
                    overallRisk === 'LOW' && 'bg-mint/30 border border-sage-light/40',
                    overallRisk === 'MEDIUM' && 'bg-butter border border-sand/40',
                    (overallRisk === 'HIGH' || overallRisk === 'SEVERE' || overallRisk === 'CRITICAL') &&
                    'bg-coral-light/10 border border-coral-light/30'
                )}
            >
                <div className="flex items-start gap-3">
                    {overallRisk !== 'LOW' && (
                        <ExclamationTriangleIcon
                            className={cn(
                                'w-5 h-5 flex-shrink-0 mt-0.5',
                                overallRisk === 'MEDIUM' && 'text-warning-600',
                                (overallRisk === 'HIGH' || overallRisk === 'SEVERE' || overallRisk === 'CRITICAL') &&
                                'text-crisis-600'
                            )}
                        />
                    )}
                    <div>
                        <p
                            className={cn(
                                'text-sm font-medium',
                                overallRisk === 'LOW' && 'text-success-800',
                                overallRisk === 'MEDIUM' && 'text-warning-800',
                                (overallRisk === 'HIGH' || overallRisk === 'SEVERE' || overallRisk === 'CRITICAL') &&
                                'text-crisis-800'
                            )}
                        >
                            {riskConfig.message}
                        </p>
                    </div>
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between">
                <p className="text-xs text-neutral-400">
                    {lastUpdated ? `Last updated: ${lastUpdated}` : 'Take an assessment to get started'}
                </p>
                <Button
                    as={Link}
                    to="/assessments"
                    variant="ghost"
                    size="sm"
                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                    className="text-terracotta hover:bg-cream"
                >
                    Take Assessment
                </Button>
            </div>
        </Card>
    );
}

export default RiskOverview;
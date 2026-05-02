import { cn } from '../../../utils/helpers';
import { CLUSTERS } from '../../../config/constants';

const clusterStyles = {
    0: { bg: 'bg-success-100', text: 'text-success-700', icon: '🌟' },
    1: { bg: 'bg-primary-100', text: 'text-primary-700', icon: '💪' },
    2: { bg: 'bg-warning-100', text: 'text-warning-700', icon: '🌱' },
    3: { bg: 'bg-accent-100', text: 'text-accent-700', icon: '🤝' },
    4: { bg: 'bg-crisis-100', text: 'text-crisis-700', icon: '❤️' },
};

function ClusterBadge({
                          clusterId = 0,
                          clusterName,
                          showIcon = true,
                          size = 'md',
                          className,
                      }) {
    const cluster = CLUSTERS[Object.keys(CLUSTERS)[clusterId]] || CLUSTERS.STABLE;
    const styles = clusterStyles[clusterId] || clusterStyles[1];
    const name = clusterName || cluster.name;

    const sizes = {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-3 py-1 text-sm',
        lg: 'px-4 py-1.5 text-base',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center gap-1.5 font-medium rounded-full',
                styles.bg,
                styles.text,
                sizes[size],
                className
            )}
        >
      {showIcon && <span>{styles.icon}</span>}
            {name}
    </span>
    );
}

export default ClusterBadge;
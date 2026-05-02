import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Card, CardHeader, CardTitle, Button, Input, EmptyState, Badge } from '../../common';
import { PeerCard } from './index';
import {
    MagnifyingGlassIcon,
    FunnelIcon,
    UserGroupIcon,
} from '@heroicons/react/24/outline';

function PeerList({
                      peers = [],
                      onMessage,
                      onConnect,
                      onViewProfile,
                      loading = false,
                      showFilters = true,
                      title = 'Community Members',
                      className,
                  }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [filter, setFilter] = useState('all'); // all, online, connected

    const filteredPeers = peers.filter((peer) => {
        // Search filter
        const matchesSearch =
            !searchQuery ||
            `${peer.firstName} ${peer.lastName}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
            peer.interests?.some((i) => i.toLowerCase().includes(searchQuery.toLowerCase()));

        // Status filter
        const matchesFilter =
            filter === 'all' ||
            (filter === 'online' && peer.status === 'online') ||
            (filter === 'connected' && peer.isConnected);

        return matchesSearch && matchesFilter;
    });

    const filterOptions = [
        { id: 'all', label: 'All' },
        { id: 'online', label: 'Online' },
        { id: 'connected', label: 'Connected' },
    ];

    return (
        <Card className={className}>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                        <UserGroupIcon className="w-5 h-5 text-neutral-400" />
                        {title}
                    </CardTitle>
                    <p className="text-sm text-neutral-500 mt-1">
                        {filteredPeers.length} members
                    </p>
                </div>

                {showFilters && (
                    <div className="flex items-center gap-2">
                        {filterOptions.map((option) => (
                            <button
                                key={option.id}
                                onClick={() => setFilter(option.id)}
                                className={cn(
                                    'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors',
                                    filter === option.id
                                        ? 'bg-primary-100 text-primary-700'
                                        : 'text-neutral-600 hover:bg-neutral-100'
                                )}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                )}
            </CardHeader>

            {/* Search */}
            {showFilters && (
                <div className="mb-4">
                    <Input
                        type="search"
                        placeholder="Search by name or interest..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        leftIcon={<MagnifyingGlassIcon className="w-4 h-4" />}
                        size="sm"
                    />
                </div>
            )}

            {/* Peer List */}
            {loading ? (
                <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="animate-pulse flex items-center gap-4 p-4 bg-neutral-50 rounded-xl">
                            <div className="w-12 h-12 bg-neutral-200 rounded-full" />
                            <div className="flex-1">
                                <div className="h-4 bg-neutral-200 rounded w-1/3 mb-2" />
                                <div className="h-3 bg-neutral-200 rounded w-1/2" />
                            </div>
                        </div>
                    ))}
                </div>
            ) : filteredPeers.length === 0 ? (
                <EmptyState
                    icon={<UserGroupIcon className="w-8 h-8" />}
                    title="No members found"
                    description={searchQuery ? 'Try adjusting your search' : 'No members match your filter'}
                />
            ) : (
                <div className="space-y-3">
                    {filteredPeers.map((peer) => (
                        <PeerCard
                            key={peer.id}
                            peer={peer}
                            onMessage={onMessage}
                            onConnect={onConnect}
                            onClick={() => onViewProfile?.(peer)}
                            isConnected={peer.isConnected}
                        />
                    ))}
                </div>
            )}
        </Card>
    );
}

export default PeerList;
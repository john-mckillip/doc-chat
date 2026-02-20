import { useCallback, useEffect, useState } from 'react';
import { fetchIndexStats } from '../utils/api';
import type { AppStats } from '../types';

export const useStats = () => {
    const [stats, setStats] = useState<AppStats | null>(null);
    const isIndexed = (stats?.total_chunks ?? 0) > 0;

    const fetchStats = useCallback(async (signal?: AbortSignal): Promise<AppStats | null> => {
        try {
            return await fetchIndexStats(signal);
        } catch (error) {
            if (signal?.aborted) {
                return null;
            }
            console.error('Failed to fetch stats:', error);
            return null;
        }
    }, []);

    const refreshStats = useCallback(async (signal?: AbortSignal) => {
        const data = await fetchStats(signal);
        if (data) {
            setStats(data);
        }
    }, [fetchStats]);

    useEffect(() => {
        const abortController = new AbortController();
        void fetchStats(abortController.signal).then(data => {
            if (data) {
                setStats(data);
            }
        });

        return () => {
            abortController.abort();
        };
    }, [fetchStats]);

    return {
        stats,
        isIndexed,
        refreshStats
    };
};

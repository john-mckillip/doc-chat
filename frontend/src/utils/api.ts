import { API_BASE_URL, WS_BASE_URL } from '../config';

export const API_ENDPOINTS = {
    stats: `${API_BASE_URL}/api/stats`,
    health: `${API_BASE_URL}/api/health`
} as const;

export const WS_ENDPOINTS = {
    chat: `${WS_BASE_URL}/ws/chat`,
    index: `${WS_BASE_URL}/ws/index`
} as const;

interface IndexStatsResponse {
    total_chunks: number;
    dimension?: number;
}

export const fetchIndexStats = async (
    signal?: AbortSignal
): Promise<IndexStatsResponse> => {
    const response = await fetch(API_ENDPOINTS.stats, { signal });

    if (!response.ok) {
        throw new Error(`Failed to fetch stats: ${response.status}`);
    }

    return response.json();
};

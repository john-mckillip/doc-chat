import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useIndexWebSocket } from '../useIndexWebSocket';
import { setupWebSocketMock, resetWebSocketMock, MockWebSocket } from '../../test/mocks/websocket';

const TEST_URL = 'ws://localhost:8000/ws/index';

let mockWs: MockWebSocket | null = null;

beforeEach(() => {
    setupWebSocketMock();

    const CapturingMockWS = new Proxy(MockWebSocket, {
        construct(Target, args: ConstructorParameters<typeof MockWebSocket>) {
            const instance = new Target(...args);
            mockWs = instance;
            return instance;
        }
    });

    (globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = CapturingMockWS;
});

afterEach(() => {
    resetWebSocketMock();
    mockWs = null;
});

async function waitForConnectionAndStart(result: { current: ReturnType<typeof useIndexWebSocket> }) {
    act(() => {
        result.current.startIndexing('/tmp/docs');
    });

    await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
    });

    await waitFor(() => expect(mockWs).not.toBeNull());
}

describe('useIndexWebSocket', () => {
    it('updates progress for valid indexing messages', async () => {
        const { result } = renderHook(() => useIndexWebSocket(TEST_URL));
        await waitForConnectionAndStart(result);

        await act(async () => {
            mockWs!.simulateMessage({ type: 'scan_start', data: { directory: '/tmp/docs' } });
        });

        expect(result.current.error).toBeNull();
        expect(result.current.progress.phase).toBe('scanning');
        expect(result.current.progress.message).toContain('Scanning directory');
    });

    it('sets error and stops indexing on malformed JSON message', async () => {
        const { result } = renderHook(() => useIndexWebSocket(TEST_URL));
        await waitForConnectionAndStart(result);

        await act(async () => {
            mockWs!.simulateMessage('{not-json');
        });

        expect(result.current.error).toBe('Received malformed indexing message');
        expect(result.current.isIndexing).toBe(false);
    });

    it('sets error from error message payload', async () => {
        const { result } = renderHook(() => useIndexWebSocket(TEST_URL));
        await waitForConnectionAndStart(result);

        await act(async () => {
            mockWs!.simulateMessage({ type: 'error', data: { message: 'index failed' } });
        });

        expect(result.current.error).toBe('index failed');
        expect(result.current.isIndexing).toBe(true);
        expect(result.current.progress.message).toContain('Error: index failed');
    });

    it('sets error and stops indexing on fatal_error', async () => {
        const { result } = renderHook(() => useIndexWebSocket(TEST_URL));
        await waitForConnectionAndStart(result);

        await act(async () => {
            mockWs!.simulateMessage({ type: 'fatal_error', data: { message: 'fatal indexer issue' } });
        });

        expect(result.current.error).toBe('fatal indexer issue');
        expect(result.current.isIndexing).toBe(false);
    });
});

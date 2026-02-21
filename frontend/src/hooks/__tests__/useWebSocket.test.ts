import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../useWebSocket';
import { setupWebSocketMock, resetWebSocketMock, MockWebSocket } from '../../test/mocks/websocket';

const TEST_URL = 'ws://localhost:8000/ws/chat';

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

/** Wait for the mock WebSocket connection to open (it uses setTimeout 0). */
async function waitForConnection(result: { current: ReturnType<typeof useWebSocket> }) {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, 10));
  });
  await waitFor(() => expect(result.current.isConnected).toBe(true));
}

describe('useWebSocket', () => {
  it('parses valid JSON messages without throwing', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    await act(async () => {
      mockWs!.simulateMessage({ type: 'sources', data: [] });
    });

    expect(result.current.error).toBeNull();
    expect(result.current.isStreaming).toBe(true);
  });

  it('does not throw and keeps error null on malformed JSON in onmessage', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    await act(async () => {
      mockWs!.simulateMessage('this is not json {{{');
    });

    expect(result.current.error).toBeNull();
    expect(result.current.isStreaming).toBe(false);
  });

  it('sets error state on error message from server', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    await act(async () => {
      mockWs!.simulateMessage({ type: 'error', data: { message: 'oops' } });
    });

    expect(result.current.error).toBe('oops');
    // Connection stays open after a non-fatal error
    expect(result.current.isConnected).toBe(true);
  });

  it('sets error state and stops streaming on fatal_error message', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    // Start streaming first so we can verify isStreaming resets
    await act(async () => {
      mockWs!.simulateMessage({ type: 'sources', data: [] });
    });
    expect(result.current.isStreaming).toBe(true);

    await act(async () => {
      mockWs!.simulateMessage({ type: 'fatal_error', data: { message: 'gone' } });
    });

    expect(result.current.error).toBe('gone');
    expect(result.current.isStreaming).toBe(false);
  });

  it('clears error state when sendMessage is called', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    // Set an error first
    await act(async () => {
      mockWs!.simulateMessage({ type: 'error', data: { message: 'prior error' } });
    });
    expect(result.current.error).toBe('prior error');

    // Sending a new message should clear the error
    await act(async () => {
      result.current.sendMessage('new question');
    });

    expect(result.current.error).toBeNull();
  });

  it('marks streaming as done on truncated message', async () => {
    const { result } = renderHook(() => useWebSocket(TEST_URL));
    await waitForConnection(result);

    await act(async () => {
      mockWs!.simulateMessage({ type: 'sources', data: [] });
    });
    expect(result.current.isStreaming).toBe(true);

    await act(async () => {
      mockWs!.simulateMessage({ type: 'truncated', data: { reason: 'max_tokens' } });
    });

    expect(result.current.isStreaming).toBe(false);
  });
});

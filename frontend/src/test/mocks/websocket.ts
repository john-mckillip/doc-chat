/**
 * Mock WebSocket implementation for testing
 */
export class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  private messageQueue: string[] = []

  constructor(url: string) {
    this.url = url

    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    this.messageQueue.push(data)
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }

  // Test helper methods
  simulateMessage(data: any): void {
    if (this.onmessage) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data)
      this.onmessage(new MessageEvent('message', { data: messageData }))
    }
  }

  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }

  simulateClose(): void {
    this.close()
  }

  getLastMessage(): string | undefined {
    return this.messageQueue[this.messageQueue.length - 1]
  }

  getAllMessages(): string[] {
    return [...this.messageQueue]
  }

  clearMessages(): void {
    this.messageQueue = []
  }
}

// Global mock WebSocket
export function setupWebSocketMock(): typeof MockWebSocket {
  (global as any).WebSocket = MockWebSocket
  return MockWebSocket
}

export function resetWebSocketMock(): void {
  delete (global as any).WebSocket
}

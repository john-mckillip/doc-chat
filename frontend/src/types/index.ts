export interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
}

export interface Source {
    file: string;
    path: string;
    chunk: number;
}

export interface WebSocketMessage {
    type: 'sources' | 'content' | 'done';
    data?: Source[] | string | Record<string, unknown>;
}

export interface UseWebSocketReturn {
    messages: Message[];
    sendMessage: (query: string) => void;
    isConnected: boolean;
    isStreaming: boolean;
}
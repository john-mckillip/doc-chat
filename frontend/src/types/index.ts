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

export interface AppStats {
    total_chunks: number;
    dimension?: number;
}

export interface IndexProgress {
    phase: string;
    currentFile: string;
    totalChunks: number;
    message: string;
}

export interface IndexStats {
    files: number;
    chunks: number;
    new: number;
    modified: number;
    unchanged: number;
    deleted: number;
}
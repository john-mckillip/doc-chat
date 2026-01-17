# DocChat Frontend

React + TypeScript frontend for the DocChat AI-powered documentation assistant.

## Features

- **Real-time Chat Interface** - WebSocket-based streaming responses from Claude AI
- **Smart Indexing UI** - Real-time progress updates during document indexing
- **Source Citations Panel** - View which documentation files informed each answer
- **Re-index Modal** - Easily re-index documentation with progress tracking
- **Modern Styling** - Tailwind CSS 4 with Vite plugin for rapid development
- **Type Safety** - Full TypeScript implementation with strict typing

## Tech Stack

- **React 19** - Latest React with modern hooks
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server with HMR
- **Tailwind CSS 4** - Utility-first styling with Vite plugin (no config needed)
- **WebSocket API** - Native browser WebSocket for real-time communication

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat.tsx              # Main chat interface with re-index modal
│   │   ├── IndexStatus.tsx       # Initial indexing screen
│   │   ├── MessageList.tsx       # Chat message display
│   │   └── SourcePanel.tsx       # Source citations sidebar
│   ├── hooks/
│   │   ├── useWebSocket.ts       # WebSocket hook for chat
│   │   └── useIndexWebSocket.ts  # WebSocket hook for indexing
│   ├── types/
│   │   └── index.ts              # TypeScript type definitions
│   ├── App.tsx                   # Root component with routing logic
│   ├── index.css                 # Global styles + Tailwind import
│   └── main.tsx                  # Application entry point
├── package.json
├── vite.config.ts                # Vite + Tailwind CSS 4 config
└── tsconfig.json                 # TypeScript configuration
```

## Development

### Prerequisites

- Node.js 18+
- Backend server running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Key Components

### Chat Component

Main chat interface with:
- Message input and send
- Real-time streaming responses
- Connection status indicator
- Re-index button and modal
- Source panel integration

### IndexStatus Component

Initial indexing screen that:
- Accepts documentation directory path
- Shows real-time indexing progress via WebSocket
- Displays stats (files, chunks, new, modified)
- Auto-transitions to chat when complete

### WebSocket Hooks

**`useWebSocket`** - Chat communication
- Manages WebSocket connection to `/ws/chat`
- Handles message history
- Streams responses in real-time
- Parses sources and content

**`useIndexWebSocket`** - Indexing progress
- Manages WebSocket connection to `/ws/index`
- Tracks indexing progress and phase
- Receives real-time file processing updates
- Reports final statistics

## Tailwind CSS 4 Configuration

This project uses Tailwind CSS 4 with the Vite plugin. No `tailwind.config.js` is needed for basic usage.

The Tailwind import is in `src/index.css`:

```css
@import "tailwindcss";
```

And the Vite plugin is configured in `vite.config.ts`:

```typescript
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

For custom configuration, you can optionally create a `tailwind.config.ts` file.

## WebSocket Message Types

### Chat WebSocket (`/ws/chat`)

**Send:**
```json
{
  "query": "How does authentication work?"
}
```

**Receive:**
- `sources` - Citation information
- `content` - Streamed response text
- `done` - Completion signal

### Index WebSocket (`/ws/index`)

**Send:**
```json
{
  "directory": "/path/to/docs"
}
```

**Receive:**
- `scan_start` - Directory scan begins
- `file_processing` - File being processed (new/modified)
- `file_processed` - File completed
- `file_skipped` - File unchanged
- `embedding_start` - Generating embeddings
- `saving` - Saving index
- `stats` - Final statistics
- `done` - Indexing complete
- `error` - Non-fatal error
- `fatal_error` - Fatal error

## Environment Configuration

The frontend connects to the backend at:
- WebSocket Chat: `ws://localhost:8000/ws/chat`
- WebSocket Index: `ws://localhost:8000/ws/index`
- REST API: `http://localhost:8000/api/stats`

To change the backend URL, update the hardcoded URLs in:
- `src/components/Chat.tsx`
- `src/components/IndexStatus.tsx`
- `src/App.tsx`

For production, consider moving these to environment variables.

## Type Definitions

See `src/types/index.ts` for TypeScript interfaces:
- `Message` - Chat message structure
- `Source` - Source citation structure
- `IndexProgress` - Indexing progress state
- `IndexStats` - Indexing statistics

## Styling Notes

### Input Text Color Fix

Custom CSS in `index.css` ensures input text is visible:

```css
input {
  color: #1a1a1a;
}

input::placeholder {
  color: #9ca3af;
}
```

### Full-Screen Layout

The app uses full viewport dimensions:

```css
#root {
  height: 100vh;
  width: 100vw;
}
```

## Common Issues

### CSS Not Loading

Ensure `@import "tailwindcss";` is at the top of `src/index.css` and the Tailwind Vite plugin is installed:

```bash
npm install -D @tailwindcss/vite
```

### WebSocket Connection Failed

- Check that the backend is running on port 8000
- Verify CORS settings in backend allow `localhost:5173` and `127.0.0.1:5173`
- Check browser console for specific connection errors

### Input Text Invisible

This is fixed with custom CSS (see Styling Notes above). If you see white text on white backgrounds, ensure `index.css` has the input color rules.

## License

MIT License - see main project LICENSE file for details

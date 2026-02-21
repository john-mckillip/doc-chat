import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'

// Mock child components
vi.mock('../components/Chat', () => ({
  Chat: () => <div data-testid="chat">Chat Component</div>
}))

vi.mock('../components/IndexStatus', () => ({
  IndexStatus: ({ onIndexComplete }: { onIndexComplete: () => void }) => (
    <div data-testid="index-status">
      IndexStatus Component{' '}
      <button onClick={onIndexComplete}>Complete</button>
    </div>
  )
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('renders without crashing', () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_chunks: 0 })
    } as Response)

    render(<App />)
    expect(screen.getByTestId('index-status')).toBeInTheDocument()
  })

  it('fetches stats on mount', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_chunks: 100 })
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('http://localhost:8000/api/stats', expect.any(Object))
    })
  })

  it('shows IndexStatus when not indexed', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_chunks: 0 })
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('index-status')).toBeInTheDocument()
    })
  })

  it('shows Chat when indexed', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total_chunks: 100 })
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('chat')).toBeInTheDocument()
    })
  })

  it('handles fetch errors gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error')
    vi.mocked(globalThis.fetch).mockRejectedValueOnce(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalled()
    })
  })

  it('refetches stats when onIndexComplete is called', async () => {
    vi.mocked(globalThis.fetch)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ total_chunks: 0 })
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ total_chunks: 100 })
      } as Response)

    const { getByText } = render(<App />)

    // Initially shows IndexStatus
    await waitFor(() => {
      expect(screen.getByTestId('index-status')).toBeInTheDocument()
    })

    // Simulate indexing complete
    const completeButton = getByText('Complete')
    completeButton.click()

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(2)
    })
  })
})

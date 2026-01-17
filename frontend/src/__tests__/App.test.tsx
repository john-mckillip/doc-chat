import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'

// Mock child components
vi.mock('../components/Chat', () => ({
  Chat: () => <div data-testid="chat">Chat Component</div>
}))

vi.mock('../components/IndexStatus', () => ({
  IndexStatus: ({ onIndexComplete }: any) => (
    <div data-testid="index-status">
      IndexStatus Component
      <button onClick={onIndexComplete}>Complete</button>
    </div>
  )
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('renders without crashing', () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ total_chunks: 0 })
    })

    render(<App />)
    expect(screen.getByTestId('index-status')).toBeInTheDocument()
  })

  it('fetches stats on mount', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ total_chunks: 100 })
    })

    render(<App />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/stats')
    })
  })

  it('shows IndexStatus when not indexed', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ total_chunks: 0 })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('index-status')).toBeInTheDocument()
    })
  })

  it('shows Chat when indexed', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      json: async () => ({ total_chunks: 100 })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('chat')).toBeInTheDocument()
    })
  })

  it('handles fetch errors gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error')
    ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalled()
    })
  })

  it('refetches stats when onIndexComplete is called', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        json: async () => ({ total_chunks: 0 })
      })
      .mockResolvedValueOnce({
        json: async () => ({ total_chunks: 100 })
      })

    const { getByText } = render(<App />)

    // Initially shows IndexStatus
    await waitFor(() => {
      expect(screen.getByTestId('index-status')).toBeInTheDocument()
    })

    // Simulate indexing complete
    const completeButton = getByText('Complete')
    completeButton.click()

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })
})

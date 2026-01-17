import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SourcePanel } from '../SourcePanel'

describe('SourcePanel', () => {
  const mockSources = [
    {
      file: 'auth.md',
      path: '/docs/auth.md',
      chunk: 0
    },
    {
      file: 'api.md',
      path: '/docs/api/endpoints.md',
      chunk: 1
    }
  ]

  it('renders source panel with title', () => {
    render(<SourcePanel sources={mockSources} />)
    expect(screen.getByText('Sources')).toBeInTheDocument()
  })

  it('renders all sources', () => {
    render(<SourcePanel sources={mockSources} />)
    expect(screen.getAllByText(/auth\.md/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/api\.md/).length).toBeGreaterThan(0)
  })

  it('numbers sources correctly', () => {
    render(<SourcePanel sources={mockSources} />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows file paths with truncation', () => {
    const { container } = render(<SourcePanel sources={mockSources} />)
    const elements = container.querySelectorAll('[title]')
    expect(elements.length).toBeGreaterThan(0)
  })

  it('includes full path in title attribute', () => {
    const { container } = render(<SourcePanel sources={mockSources} />)
    const element = container.querySelector('[title="/docs/auth.md"]')
    expect(element).toBeInTheDocument()
  })

  it('renders single source', () => {
    render(<SourcePanel sources={[mockSources[0]]} />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getAllByText(/auth\.md/).length).toBeGreaterThan(0)
  })

  it('applies correct styling classes', () => {
    const { container } = render(<SourcePanel sources={mockSources} />)
    const panel = container.firstChild
    expect(panel).toHaveClass('w-80')
  })
})

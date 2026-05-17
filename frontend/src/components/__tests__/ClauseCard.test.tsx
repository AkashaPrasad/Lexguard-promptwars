import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ClauseCard } from '../ClauseCard'
import type { ScoredClause } from '../../types'

const mockClause: ScoredClause = {
  clause_type: 'Non-Compete',
  extracted_text: 'Party shall not compete for 5 years worldwide.',
  confidence: 0.92,
  risk_score: 9,
  severity: 'CRITICAL',
  risk_category: 'Employment',
  explanation: 'This is an extremely restrictive non-compete clause.',
  adversarial_analysis: 'The other party can enforce this to prevent you from working.',
  negotiation_tip: 'Negotiate to limit geographic scope and duration.',
  worst_case_scenario: 'You cannot work in your industry anywhere for 5 years.',
}

const mockLowClause: ScoredClause = {
  clause_type: 'Governing Law',
  extracted_text: 'This agreement is governed by California law.',
  confidence: 0.95,
  risk_score: 3,
  severity: 'LOW',
  risk_category: 'Compliance',
  explanation: 'Standard governing law clause.',
  adversarial_analysis: '',
  negotiation_tip: 'Negotiate for home jurisdiction if possible.',
  worst_case_scenario: '',
}

describe('ClauseCard', () => {
  it('renders clause type and severity badge', () => {
    render(<ClauseCard clause={mockClause} />)
    expect(screen.getByText('Non-Compete')).toBeInTheDocument()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('shows risk score', () => {
    render(<ClauseCard clause={mockClause} />)
    expect(screen.getByText('9/10')).toBeInTheDocument()
  })

  it('is collapsed by default', () => {
    render(<ClauseCard clause={mockClause} />)
    expect(screen.queryByText('Extracted Text')).not.toBeInTheDocument()
  })

  it('expands when clicked', () => {
    render(<ClauseCard clause={mockClause} />)
    const button = screen.getByRole('button')
    fireEvent.click(button)
    expect(screen.getByText('Extracted Text')).toBeInTheDocument()
    expect(screen.getByText('This is an extremely restrictive non-compete clause.')).toBeInTheDocument()
  })

  it('collapses when clicked again', () => {
    render(<ClauseCard clause={mockClause} />)
    const button = screen.getByRole('button')
    fireEvent.click(button)
    fireEvent.click(button)
    expect(screen.queryByText('Extracted Text')).not.toBeInTheDocument()
  })

  it('shows adversarial analysis when expanded and non-empty', () => {
    render(<ClauseCard clause={mockClause} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('Why This Matters')).toBeInTheDocument()
  })

  it('hides adversarial analysis section when empty', () => {
    render(<ClauseCard clause={mockLowClause} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.queryByText('Why This Matters')).not.toBeInTheDocument()
  })

  it('shows negotiation tip when expanded', () => {
    render(<ClauseCard clause={mockClause} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('What to Negotiate')).toBeInTheDocument()
    expect(
      screen.getByText('Negotiate to limit geographic scope and duration.')
    ).toBeInTheDocument()
  })

  it('has correct aria-expanded attribute', () => {
    render(<ClauseCard clause={mockClause} />)
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('renders LOW severity with Shield icon class', () => {
    render(<ClauseCard clause={mockLowClause} />)
    expect(screen.getByText('LOW')).toBeInTheDocument()
  })

  it('applies correct severity background color class', () => {
    render(<ClauseCard clause={mockClause} />)
    const badge = screen.getByLabelText('CRITICAL risk')
    expect(badge).toHaveClass('bg-red-100')
    expect(badge).toHaveClass('text-red-800')
  })
})

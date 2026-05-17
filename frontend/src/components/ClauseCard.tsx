import React, { memo, useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, Shield, Info } from 'lucide-react'
import type { ScoredClause } from '../types'
import { SEVERITY_BG_COLORS } from '../constants'

interface ClauseCardProps {
  clause: ScoredClause
}

function SeverityIcon({ severity }: { severity: string }): React.ReactElement {
  if (severity === 'CRITICAL' || severity === 'HIGH') {
    return <AlertTriangle aria-hidden="true" size={12} />
  }
  if (severity === 'MEDIUM') {
    return <Info aria-hidden="true" size={12} />
  }
  return <Shield aria-hidden="true" size={12} />
}

export const ClauseCard: React.FC<ClauseCardProps> = memo(({ clause }) => {
  const [expanded, setExpanded] = useState(false)
  const badgeClass = SEVERITY_BG_COLORS[clause.severity]

  return (
    <div className="border border-slate-200 rounded-lg mb-3 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={`${clause.clause_type} clause - ${clause.severity} risk. Click to ${expanded ? 'collapse' : 'expand'}`}
      >
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${badgeClass}`}
            aria-label={`${clause.severity} risk`}
          >
            <SeverityIcon severity={clause.severity} />
            {clause.severity}
          </span>
          <span className="font-medium text-slate-800">{clause.clause_type}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">{clause.risk_score}/10</span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-100">
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
              Extracted Text
            </h4>
            <p className="font-mono text-sm bg-slate-50 p-3 rounded border text-slate-700">
              {clause.extracted_text}
            </p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
              Explanation
            </h4>
            <p className="text-sm text-slate-700">{clause.explanation}</p>
          </div>
          {clause.adversarial_analysis && (
            <div>
              <h4 className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1">
                Why This Matters
              </h4>
              <p className="text-sm text-slate-700">{clause.adversarial_analysis}</p>
            </div>
          )}
          {clause.worst_case_scenario && (
            <div>
              <h4 className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-1">
                Worst Case Scenario
              </h4>
              <p className="text-sm text-slate-700">{clause.worst_case_scenario}</p>
            </div>
          )}
          <div>
            <h4 className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-1">
              What to Negotiate
            </h4>
            <p className="text-sm text-slate-700">{clause.negotiation_tip}</p>
          </div>
        </div>
      )}
    </div>
  )
})

ClauseCard.displayName = 'ClauseCard'

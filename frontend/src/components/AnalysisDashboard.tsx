import React, { useEffect, useRef } from 'react'
import { Download, RefreshCw, FileText, Scale, Calendar, MapPin, Clock } from 'lucide-react'
import { RiskMeter } from './RiskMeter'
import { ClauseCard } from './ClauseCard'
import type { AnalysisResult } from '../types'
import { downloadReport } from '../api/client'

interface AnalysisDashboardProps {
  result: AnalysisResult
  onReset: () => void
}

function MetadataItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string | null | undefined
}): React.ReactElement | null {
  if (!value) return null
  return (
    <div className="flex items-start gap-2">
      <span className="text-slate-400 mt-0.5 shrink-0">{icon}</span>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-medium text-slate-800">{value}</p>
      </div>
    </div>
  )
}

async function triggerPdfDownload(analysisId: string, filename: string): Promise<void> {
  const blob = await downloadReport(analysisId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `lexguard-report-${filename}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export function AnalysisDashboard({ result, onReset }: AnalysisDashboardProps): React.ReactElement {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const sortedClauses = [...result.clauses].sort((a, b) => b.risk_score - a.risk_score)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="text-2xl font-bold text-slate-800 outline-none"
        >
          Analysis Results
        </h2>
        <div className="flex gap-3">
          <button
            onClick={() => triggerPdfDownload(result.analysis_id, result.filename)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <Download size={16} aria-hidden="true" />
            Download PDF
          </button>
          <button
            onClick={onReset}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm"
          >
            <RefreshCw size={16} aria-hidden="true" />
            New Analysis
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center">
          <RiskMeter score={result.overall_risk_score} severity={result.overall_severity} />
        </div>

        <div className="md:col-span-2 bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <FileText size={18} aria-hidden="true" />
            Contract Details
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <MetadataItem
              icon={<Scale size={16} />}
              label="Contract Type"
              value={result.metadata.contract_type}
            />
            <MetadataItem
              icon={<MapPin size={16} />}
              label="Governing Law"
              value={result.metadata.governing_law}
            />
            <MetadataItem
              icon={<Calendar size={16} />}
              label="Effective Date"
              value={result.metadata.effective_date}
            />
            <MetadataItem
              icon={<Clock size={16} />}
              label="Duration"
              value={result.metadata.contract_duration}
            />
          </div>
          {result.metadata.parties.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 mb-1">Parties</p>
              <div className="flex flex-wrap gap-2">
                {result.metadata.parties.map((party, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-sm"
                  >
                    {party}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {result.summary && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h3 className="font-semibold text-amber-800 mb-2">Executive Summary</h3>
          <p className="text-sm text-amber-900">{result.summary}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800 mb-4">
          Clause Analysis ({result.clauses.length} clauses identified)
        </h3>
        {sortedClauses.length === 0 ? (
          <p className="text-slate-500 text-sm">No clauses were identified in this document.</p>
        ) : (
          <div>
            {sortedClauses.map((clause, index) => (
              <ClauseCard key={`${clause.clause_type}-${index}`} clause={clause} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

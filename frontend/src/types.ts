export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
export type RiskCategory =
  | 'Financial'
  | 'Privacy'
  | 'IP/Ownership'
  | 'Employment'
  | 'Operational'
  | 'Compliance'
  | 'Termination'

export interface ScoredClause {
  clause_type: string
  extracted_text: string
  confidence: number
  risk_score: number
  severity: RiskSeverity
  risk_category: RiskCategory
  explanation: string
  adversarial_analysis: string
  negotiation_tip: string
  worst_case_scenario: string
}

export interface ContractMetadata {
  contract_type: string
  parties: string[]
  effective_date: string | null
  governing_law: string | null
  contract_duration: string | null
}

export interface AnalysisResult {
  analysis_id: string
  filename: string
  overall_risk_score: number
  overall_severity: RiskSeverity
  clauses: ScoredClause[]
  metadata: ContractMetadata
  highlighted_html: string
  summary: string
  indian_law_flags: string[]
  created_at: string
}

export interface UploadState {
  status: 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error'
  progress: number
  error: string | null
}

import axios from 'axios'
import type { AnalysisResult } from '../types'
import { API_BASE_URL } from '../constants'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

export async function analyzeContract(file: File): Promise<AnalysisResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<AnalysisResult>('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

  return response.data
}

export async function downloadReport(analysisId: string): Promise<Blob> {
  const response = await apiClient.get(`/report/${analysisId}`, {
    responseType: 'blob',
  })
  return response.data
}

export async function getAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await apiClient.get<AnalysisResult>(`/analysis/${analysisId}`)
  return response.data
}

export async function fetchDemo(): Promise<AnalysisResult> {
  const response = await apiClient.get<AnalysisResult>('/demo')
  return response.data
}

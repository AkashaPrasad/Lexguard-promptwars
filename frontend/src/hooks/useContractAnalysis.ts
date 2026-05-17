import { useState, useCallback } from 'react'
import type { AnalysisResult, UploadState } from '../types'
import { analyzeContract } from '../api/client'
import { MAX_FILE_SIZE_BYTES, ALLOWED_FILE_TYPES } from '../constants'

interface UseContractAnalysis {
  result: AnalysisResult | null
  uploadState: UploadState
  analyze: (file: File) => Promise<void>
  reset: () => void
}

function validateFile(file: File): string | null {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large. Maximum size is 10MB.`
  }
  if (!ALLOWED_FILE_TYPES.includes(file.type)) {
    return `Unsupported file type. Please upload PDF, DOCX, or image files.`
  }
  return null
}

export function useContractAnalysis(): UseContractAnalysis {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    error: null,
  })

  const reset = useCallback(() => {
    setResult(null)
    setUploadState({ status: 'idle', progress: 0, error: null })
  }, [])

  const analyze = useCallback(async (file: File): Promise<void> => {
    const validationError = validateFile(file)
    if (validationError) {
      setUploadState({ status: 'error', progress: 0, error: validationError })
      return
    }

    setUploadState({ status: 'uploading', progress: 10, error: null })

    try {
      setUploadState({ status: 'analyzing', progress: 40, error: null })
      const analysisResult = await analyzeContract(file)
      setUploadState({ status: 'complete', progress: 100, error: null })
      setResult(analysisResult)
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Analysis failed. Please try again.'
      setUploadState({ status: 'error', progress: 0, error: message })
    }
  }, [])

  return { result, uploadState, analyze, reset }
}

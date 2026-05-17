import React, { lazy, Suspense, useState } from 'react'
import { UploadZone } from './components/UploadZone'
import { ErrorBoundary } from './components/ErrorBoundary'
import type { AnalysisResult } from './types'
import { analyzeContract, fetchDemo } from './api/client'

const AnalysisDashboard = lazy(() =>
  import('./components/AnalysisDashboard').then((m) => ({ default: m.AnalysisDashboard }))
)

function App(): React.ReactElement {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async (file: File): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await analyzeContract(file)
      setResult(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Analysis failed'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDemo = async (): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchDemo()
      setResult(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Demo failed to load'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 font-inter">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="text-2xl font-bold text-slate-800">LexGuard</div>
          <span className="text-sm text-slate-500">Contract Risk Analyzer</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <ErrorBoundary>
          {!result && (
            <>
              <UploadZone onUpload={handleUpload} isLoading={isLoading} error={error} />
              <div className="text-center mt-4">
                <button
                  onClick={handleDemo}
                  disabled={isLoading}
                  className="text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Load instant demo analysis without uploading a file"
                >
                  {isLoading ? 'Loading...' : 'Try Demo — see a sample analysis instantly'}
                </button>
              </div>
            </>
          )}

          {result && (
            <Suspense
              fallback={
                <div
                  aria-busy="true"
                  aria-label="Loading analysis..."
                  className="text-center py-8"
                >
                  Loading analysis...
                </div>
              }
            >
              <AnalysisDashboard result={result} onReset={() => setResult(null)} />
            </Suspense>
          )}
        </ErrorBoundary>
      </main>
    </div>
  )
}

export default App

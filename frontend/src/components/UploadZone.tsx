import React, { useCallback, useRef, useState } from 'react'
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, ALLOWED_FILE_TYPES } from '../constants'

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>
  isLoading: boolean
  error: string | null
}

function validateClientSide(file: File): string | null {
  if (!ALLOWED_FILE_TYPES.includes(file.type)) {
    return `Unsupported file type. Please upload: ${ALLOWED_EXTENSIONS.join(', ')}`
  }
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    return `File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.`
  }
  return null
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUpload, isLoading, error }) => {
  const [isDragOver, setIsDragOver] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const errorId = 'upload-error'

  const handleFile = useCallback(
    async (file: File) => {
      const validationError = validateClientSide(file)
      if (validationError) {
        setLocalError(validationError)
        return
      }
      setLocalError(null)
      await onUpload(file)
    },
    [onUpload]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const displayError = localError || error

  return (
    <div className="max-w-2xl mx-auto mt-12">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Contract Risk Analyzer</h1>
        <p className="text-slate-600">
          Upload a contract to get an instant AI-powered risk assessment
        </p>
      </div>

      <div
        role="region"
        aria-label="File upload area"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
          ${isDragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50'}
          ${isLoading ? 'cursor-not-allowed opacity-75' : ''}
        `}
        aria-describedby={displayError ? errorId : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(',')}
          onChange={handleInputChange}
          className="hidden"
          disabled={isLoading}
          aria-label="Choose a contract file to upload"
        />

        {isLoading ? (
          <div aria-live="polite" aria-label="Analyzing contract...">
            <Loader2
              className="mx-auto mb-4 text-blue-500 animate-spin"
              size={48}
              aria-hidden="true"
            />
            <p className="text-lg font-medium text-slate-700">Analyzing your contract...</p>
            <p className="text-sm text-slate-500 mt-1">This may take up to 60 seconds</p>
          </div>
        ) : (
          <>
            {isDragOver ? (
              <FileText className="mx-auto mb-4 text-blue-500" size={48} aria-hidden="true" />
            ) : (
              <Upload className="mx-auto mb-4 text-slate-400" size={48} aria-hidden="true" />
            )}
            <p className="text-lg font-medium text-slate-700 mb-1">
              {isDragOver ? 'Drop your contract here' : 'Drag & drop your contract'}
            </p>
            <p className="text-sm text-slate-500 mb-4">or click to browse files</p>
            <p className="text-xs text-slate-400">
              Supported: PDF, DOCX, DOC, PNG, JPG &bull; Max {MAX_FILE_SIZE_MB}MB
            </p>
          </>
        )}
      </div>

      {displayError && (
        <div
          id={errorId}
          role="alert"
          aria-live="assertive"
          className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
        >
          <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={18} aria-hidden="true" />
          <p className="text-sm text-red-700">{displayError}</p>
        </div>
      )}
    </div>
  )
}

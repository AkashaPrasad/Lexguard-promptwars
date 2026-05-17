import React, { useEffect, useState } from 'react'

interface RiskMeterProps {
  score: number
  severity: string
}

function getColor(s: number): string {
  if (s >= 70) return '#DC2626'
  if (s >= 50) return '#EA580C'
  if (s >= 30) return '#D97706'
  return '#16A34A'
}

export const RiskMeter: React.FC<RiskMeterProps> = ({ score, severity }) => {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    let current = 0
    const target = score
    const increment = target / 60
    const timer = setInterval(() => {
      current = Math.min(current + increment, target)
      setDisplayScore(Math.round(current))
      if (current >= target) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [score])

  const color = getColor(score)
  const circumference = 2 * Math.PI * 60
  const offset = circumference - (displayScore / 100) * circumference

  return (
    <div
      className="flex flex-col items-center"
      role="img"
      aria-label={`Overall risk score: ${score} out of 100, ${severity} risk`}
    >
      <svg width="160" height="160" viewBox="0 0 160 160" aria-hidden="true">
        <circle cx="80" cy="80" r="60" fill="none" stroke="#E5E7EB" strokeWidth="12" />
        <circle
          cx="80"
          cy="80"
          r="60"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 0.05s' }}
        />
        <text x="80" y="75" textAnchor="middle" fontSize="28" fontWeight="bold" fill={color}>
          {displayScore}
        </text>
        <text x="80" y="98" textAnchor="middle" fontSize="12" fill="#6B7280">
          /100
        </text>
      </svg>
      <span className="text-sm font-semibold mt-2" style={{ color }}>
        {severity} RISK
      </span>
      <span className="text-xs text-slate-600 mt-1">Overall Contract Risk Score</span>
    </div>
  )
}

/**
 * ChartMessage.jsx
 * -----------------
 * Renders a chart.js chart inside a chat bubble using react-chartjs-2.
 * Handles: line, bar, area (filled line) chart types.
 *
 * Props:
 *   chartData   – JSON from /api/graphs/* (labels, datasets, title, summary, y_axis_label)
 *   isLoading   – show skeleton while fetching
 *   error       – show error state
 *   activeType  – "line" | "bar" | "area"  (controlled by parent toggle)
 */

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import './ChartMessage.css'

// Register chart.js modules once
ChartJS.register(
  CategoryScale, LinearScale,
  PointElement, LineElement,
  BarElement,
  Title, Tooltip, Legend, Filler,
)

// ── Build chart.js options ────────────────────────────────────────────────────
function buildOptions(yLabel = 'Annual Growth (%)', chartType = 'line') {
  const isPercent = /%|growth|rate|unemployment/i.test(String(yLabel || ''))
  return {
    responsive:          true,
    maintainAspectRatio: false,
    animation:           { duration: 500 },
    interaction:         { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          font:           { size: 11, family: "'Inter', system-ui, sans-serif" },
          color:          '#374151',
          boxWidth:       12,
          padding:        16,
          usePointStyle:  true,
          pointStyle:     'circle',
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        titleFont:  { size: 12, weight: '600' },
        bodyFont:   { size: 11 },
        padding:    10,
        borderColor: 'rgba(255,255,255,0.08)',
        borderWidth: 1,
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed.y
            if (v === null || v === undefined) return ` ${ctx.dataset.label}: N/A`
            const sign = v > 0 ? '+' : ''
            if (isPercent) return ` ${ctx.dataset.label}: ${sign}${v.toFixed(2)}%`
            return ` ${ctx.dataset.label}: ${v.toLocaleString()}`
          },
        },
      },
    },
    scales: {
      x: {
        grid:  { color: 'rgba(107,114,128,0.08)' },
        ticks: {
          font:       { size: 10 },
          color:      '#6b7280',
          maxRotation: 45,
          minRotation: 0,
        },
      },
      y: {
        grid:  { color: 'rgba(107,114,128,0.08)' },
        ticks: {
          font:     { size: 10 },
          color:    '#6b7280',
          callback: (v) => {
            if (isPercent) return `${v > 0 ? '+' : ''}${v}%`
            return Number(v).toLocaleString()
          },
        },
        title: {
          display: true,
          text:    yLabel,
          color:   '#9ca3af',
          font:    { size: 10 },
        },
      },
    },
  }
}

// ── Trend pill ────────────────────────────────────────────────────────────────
function TrendPill({ sector, info }) {
  const arrow = info.trend === 'up' ? '▲' : info.trend === 'down' ? '▼' : '→'
  const cls   = info.trend === 'up' ? 'trend-up' : info.trend === 'down' ? 'trend-down' : 'trend-stable'
  const sign  = info.change_pct > 0 ? '+' : ''
  return (
    <div className={`trend-pill ${cls}`}>
      <span className="trend-sector">{sector}</span>
      <span className="trend-arrow">{arrow}</span>
      <span className="trend-val">{sign}{info.change_pct} pp</span>
      <span className="trend-avg">avg {info.avg > 0 ? '+' : ''}{info.avg}%</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ChartMessage({ chartData, isLoading, error, activeType = 'line' }) {

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="chart-bubble">
        <div className="chart-skeleton">
          <div className="skel skel-title" />
          <div className="skel skel-chart" />
          <div className="skel skel-pills" />
        </div>
      </div>
    )
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error || !chartData) {
    return (
      <div className="chart-bubble chart-bubble--error">
        ⚠️ Could not load chart data from the warehouse. Please try again.
      </div>
    )
  }

  const {
    title,
    subtitle,
    labels,
    datasets,
    summary,
    y_axis_label = 'Annual Growth (%)',
  } = chartData

  // Build datasets with area fill if needed
  const resolvedDatasets = datasets.map(ds => {
    const d = { ...ds }
    if (activeType === 'area') {
      d.fill = true
    } else {
      delete d.fill
    }
    return d
  })

  const data    = { labels, datasets: resolvedDatasets }
  const options = buildOptions(y_axis_label, activeType)

  return (
    <div className="chart-bubble">
      {/* Header */}
      <div className="chart-header">
        <span className="chart-title-icon">📈</span>
        <div>
          <h4 className="chart-title">{title}</h4>
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
      </div>

      {/* Chart canvas */}
      <div className="chart-canvas-wrap">
        {activeType === 'bar'
          ? <Bar  data={data} options={options} />
          : <Line data={data} options={options} />
        }
      </div>

      {/* Summary trend pills */}
      {summary && Object.keys(summary).length > 0 && (
        <div className="chart-summary">
          <p className="chart-summary-label">Trend ({Object.values(summary)[0]?.start_year}→{Object.values(summary)[0]?.end_year})</p>
          <div className="chart-trends">
            {Object.entries(summary).map(([sector, info]) => (
              <TrendPill key={sector} sector={sector} info={info} />
            ))}
          </div>
        </div>
      )}

      {/* Source note */}
      <p className="chart-source">
        📌 Source: Central Bank of Sri Lanka via Econex Data Warehouse.
      </p>
    </div>
  )
}

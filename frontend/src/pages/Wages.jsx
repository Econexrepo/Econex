import { useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import api from '../api/axios'
import './Dashboard.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
  Filler
)

// ─────────────────────────────────────────────────────────
// Chart helpers
// ─────────────────────────────────────────────────────────
function wageTrendDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  const years = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)
  const categories = [...new Set(data.map((d) => d.category))]

  const LINE_COLORS = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#06b6d4',
    '#ec4899',
    '#84cc16',
  ]

  const datasets = categories.map((category, idx) => {
    const yearValueMap = new Map()

    data
      .filter((d) => d.category === category)
      .forEach((d) => {
        yearValueMap.set(Number(d.year), Number(d.value))
      })

    return {
      label: category,
      data: years.map((y) => yearValueMap.get(y) ?? null),
      borderColor: LINE_COLORS[idx % LINE_COLORS.length],
      backgroundColor: LINE_COLORS[idx % LINE_COLORS.length],
      tension: 0.25,
      fill: false,
      pointRadius: 2,
      pointHoverRadius: 4,
      borderWidth: 2,
    }
  })

  return {
    labels: years,
    datasets,
  }
}

function wageLongRunEffectDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: 'Long-run Effect',
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.value >= 0 ? 'rgba(34,197,94,0.85)' : 'rgba(239,68,68,0.85)'
        ),
        borderColor: data.map((d) =>
          d.value >= 0 ? 'rgba(22,163,74,1)' : 'rgba(220,38,38,1)'
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}

function wageShortRunEffectDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: 'Short-run Effect',
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.is_significant ? 'rgba(34,197,94,0.85)' : 'rgba(239,68,68,0.85)'
        ),
        borderColor: data.map((d) =>
          d.is_significant ? 'rgba(22,163,74,1)' : 'rgba(220,38,38,1)'
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}

const wageTrendOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      labels: {
        boxWidth: 12,
        padding: 12,
        font: { size: 11 },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(1)}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      title: {
        display: true,
        text: 'Year',
      },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 10,
      },
    },
    y: {
      beginAtZero: false,
      grid: { color: '#e5e7eb' },
      title: {
        display: true,
        text: 'Wage Index',
      },
    },
  },
}

const wageLongRunOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const val = Number(ctx.raw)
          return `Long-run effect: ${val.toExponential(3)}`
        },
      },
    },
  },
  scales: {
    x: {
      grid: { color: '#e5e7eb' },
      title: {
        display: true,
        text: 'Long-run effect (coefficient)',
      },
      ticks: {
        callback: (v) => Number(v).toExponential(1),
      },
    },
    y: {
      grid: { display: false },
      ticks: { autoSkip: false },
    },
  },
}

const wageShortRunOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const val = Number(ctx.raw)
          return `Short-run effect: ${val.toExponential(3)}`
        },
      },
    },
  },
  scales: {
    x: {
      grid: { color: '#e5e7eb' },
      title: {
        display: true,
        text: 'Short-run effect (coefficient)',
      },
      ticks: {
        callback: (v) => Number(v).toExponential(1),
      },
    },
    y: {
      grid: { display: false },
      ticks: { autoSkip: false },
    },
  },
}

const lineOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

const gdpTrendOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      labels: {
        boxWidth: 12,
        padding: 12,
        font: { size: 11 },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(2)}%`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      title: {
        display: true,
        text: 'Year',
      },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 10,
      },
    },
    y: {
      grid: { color: '#e5e7eb' },
      title: {
        display: true,
        text: 'GDP Growth (%)',
      },
      ticks: {
        callback: (v) => `${v}%`,
      },
    },
  },
}

// ─────────────────────────────────────────────────────────
// Chart card
// ─────────────────────────────────────────────────────────
function ChartCard({ title, children, height = 220 }) {
  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div style={{ height }}>{children}</div>
    </div>
  )
}

function gdpSectorTrendDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  const years = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)
  const categories = [...new Set(data.map((d) => d.category))]

  const LINE_COLORS = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#06b6d4',
    '#ec4899',
    '#84cc16',
  ]

  const datasets = categories.map((category, idx) => {
    const yearValueMap = new Map()

    data
      .filter((d) => d.category === category)
      .forEach((d) => {
        yearValueMap.set(Number(d.year), Number(d.value))
      })

    return {
      label: category,
      data: years.map((y) => yearValueMap.get(y) ?? null),
      borderColor: LINE_COLORS[idx % LINE_COLORS.length],
      backgroundColor: LINE_COLORS[idx % LINE_COLORS.length],
      tension: 0.25,
      fill: false,
      pointRadius: 2,
      pointHoverRadius: 4,
      borderWidth: 2,
    }
  })

  return {
    labels: years,
    datasets,
  }
}

// ─────────────────────────────────────────────────────────
// Main Dashboard
// ─────────────────────────────────────────────────────────
export default function Dashboard() {
  const [charts, setCharts] = useState({})
  const [rsui, setRsui] = useState([])
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [statsRes, rsRes, insRes] = await Promise.all([
          api.get('/api/dashboard/stats'),
          api.get('/api/dashboard/rsui-trend'),
          api.get('/api/dashboard/insights'),
        ])

        setRsui(rsRes.data.data || [])
        setInsights(insRes.data.insights || [])

        const chartNames = [
          'gdp-sector-trend'
        ]

        const chartResults = await Promise.allSettled(
          chartNames.map((c) => api.get(`/api/gdp/charts/${c}`))
        )

        const chartData = {}

        chartNames.forEach((name, i) => {
          const result = chartResults[i]
          if (result.status === 'fulfilled') {
            chartData[name] = result.value.data?.data || []
          } else {
            console.error(`Failed to load chart: ${name}`, result.reason)
            chartData[name] = []
          }
        })

        setCharts(chartData)
      } catch (err) {
        console.error('Dashboard API error', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  if (loading) {
    return <div className="dashboard">Loading dashboard...</div>
  }

  const rsuiLine = {
    labels: Array.isArray(rsui) ? rsui.map((r) => r.year) : [],
    datasets: [
      {
        data: Array.isArray(rsui) ? rsui.map((r) => r.value) : [],
        borderColor: '#e8614a',
        backgroundColor: 'rgba(232,97,74,.12)',
        fill: true,
        tension: 0.4,
      },
    ],
  }

  return (
    <div className="dashboard">
      <div className="charts-grid">
        {Array.isArray(gdpSectorTrend) && gdpSectorTrend.length > 0 && (
          <ChartCard title="GDP Growth Trend by Sector" height={420}>
            <Line
              data={gdpSectorTrendDataset(gdpSectorTrend)}
              options={gdpTrendOpts}
            />
          </ChartCard>
        )}

        {Array.isArray(charts['wage-real-trend']) &&
          charts['wage-real-trend'].length > 0 && (
            <ChartCard title="Real Wage Trend by Category" height={420}>
              <Line
                data={wageTrendDataset(charts['wage-real-trend'])}
                options={wageTrendOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(charts['wage-longrun-effect']) &&
          charts['wage-longrun-effect'].length > 0 && (
            <ChartCard title="Long-run ARDL Effect by Wage Category" height={360}>
              <Bar
                data={wageLongRunEffectDataset(charts['wage-longrun-effect'])}
                options={wageLongRunOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(charts['wage-shortrun-effect']) &&
          charts['wage-shortrun-effect'].length > 0 && (
            <ChartCard title="Short-run ARDL Effect by Wage Category" height={360}>
              <Bar
                data={wageShortRunEffectDataset(charts['wage-shortrun-effect'])}
                options={wageShortRunOpts}
              />
            </ChartCard>
          )}
      </div>

      <div className="rsui-card">
        <h3 className="chart-title">Overall RSUI Trend</h3>
        <div style={{ height: 220 }}>
          <Line data={rsuiLine} options={lineOpts} />
        </div>
      </div>

      <div className="insights-section">
        {Array.isArray(insights) &&
          insights.map((ins) => (
            <div key={ins.id} className={`insight-card insight-${ins.type}`}>
              <span>{ins.icon}</span>
              <strong>{ins.title}</strong>
              <p>{ins.description}</p>
            </div>
          ))}
      </div>
    </div>
  )
}
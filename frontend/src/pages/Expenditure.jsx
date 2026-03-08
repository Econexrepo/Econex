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
import { Bar, Line } from 'react-chartjs-2'
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
function expenditureTypeTrendDataset(data = []) {
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

  return { labels: years, datasets }
}

function totalExpenditureLineDataset(data = []) {
  return {
    labels: data.map((d) => d.year),
    datasets: [
      {
        label: 'Total Expenditure',
        data: data.map((d) => d.value),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.12)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      },
    ],
  }
}

function longRunEffectBarDataset(data = []) {
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

function shortRunEffectBarDataset(data = []) {
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

// ─────────────────────────────────────────────────────────
// Chart options
// ─────────────────────────────────────────────────────────
const lineOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

const expenditureTrendOpts = {
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
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString()}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 10,
      },
      title: {
        display: true,
        text: 'Year',
      },
    },
    y: {
      beginAtZero: false,
      grid: { color: '#e5e7eb' },
      title: {
        display: true,
        text: 'Expenditure (Rs. Mn)',
      },
      ticks: {
        callback: (v) => Number(v).toLocaleString(),
      },
    },
  },
}

const totalExpenditureTrendOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString()}`,
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
        text: 'Expenditure (Rs. Mn)',
      },
      ticks: {
        callback: (v) => Number(v).toLocaleString(),
      },
    },
  },
}

const longRunEffectOpts = {
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

const shortRunEffectOpts = {
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

// ─────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────
export default function Expenditure() {
  const [charts, setCharts] = useState({})
  const [rsui, setRsui] = useState([])
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [, rsRes, insRes] = await Promise.all([
          api.get('/api/dashboard/stats'),
          api.get('/api/dashboard/rsui-trend'),
          api.get('/api/dashboard/insights'),
        ])

        setRsui(rsRes.data?.data || [])
        setInsights(insRes.data?.insights || [])

        const chartNames = [
          'expenditure-type-trend',
          'total-expenditure-trend',
          'type-longrun-effect',
          'type-shortrun-effect',
        ]

        const chartResults = await Promise.allSettled(
          chartNames.map((c) => api.get(`/api/government-expenditure/charts/${c}`))
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
        console.error('Government Expenditure API error', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  if (loading) {
    return <div className="dashboard">Loading government expenditure dashboard...</div>
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
        {Array.isArray(charts['expenditure-type-trend']) &&
          charts['expenditure-type-trend'].length > 0 && (
            <ChartCard title="Government Expenditure by Type Trend" height={420}>
              <Line
                data={expenditureTypeTrendDataset(charts['expenditure-type-trend'])}
                options={expenditureTrendOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(charts['total-expenditure-trend']) &&
          charts['total-expenditure-trend'].length > 0 && (
            <ChartCard title="Total Government Expenditure Trend" height={380}>
              <Line
                data={totalExpenditureLineDataset(charts['total-expenditure-trend'])}
                options={totalExpenditureTrendOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(charts['type-longrun-effect']) &&
          charts['type-longrun-effect'].length > 0 && (
            <ChartCard title="Long-run ARDL Effect by Expenditure Type" height={360}>
              <Bar
                data={longRunEffectBarDataset(charts['type-longrun-effect'])}
                options={longRunEffectOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(charts['type-shortrun-effect']) &&
          charts['type-shortrun-effect'].length > 0 && (
            <ChartCard title="Short-run ARDL Effect by Expenditure Type" height={360}>
              <Bar
                data={shortRunEffectBarDataset(charts['type-shortrun-effect'])}
                options={shortRunEffectOpts}
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
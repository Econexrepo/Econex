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
// Colors
// ─────────────────────────────────────────────────────────
const BAR_COLORS = [
  '#7c6ff7',
  '#e8614a',
  '#10b981',
  '#f59e0b',
  '#3b82f6',
  '#ec4899',
]

// ─────────────────────────────────────────────────────────
// Chart helpers
// ─────────────────────────────────────────────────────────
function barDataset(data) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        data: data.map((d) => d.value),
        backgroundColor: data.map(
          (_, i) => BAR_COLORS[i % BAR_COLORS.length]
        ),
        borderRadius: 6,
        categoryPercentage: 0.6, 
        barPercentage: 0.7,      
      },
    ],
  }
}


function gdpTrendDataset(data = []) {
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

function gdpStackedDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  const years = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)
  const categories = [...new Set(data.map((d) => d.category))]

  const STACK_COLORS = [
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
      data: years.map((y) => yearValueMap.get(y) ?? 0),
      backgroundColor: STACK_COLORS[idx % STACK_COLORS.length],
      borderRadius: 4,
      borderWidth: 0,
      stack: 'gdp',
    }
  })

  return {
    labels: years,
    datasets,
  }
}

const barOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,

  layout: {
    padding: {
      top: 10,
      right: 20,
      bottom: 10,
      left: 10,
    },
  },

  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      enabled: true,
    },
  },

  scales: {
    x: {
      grid: {
        color: '#e5e7eb',
      },
      ticks: {
        padding: 10,
        font: {
          size: 11,
        },
      },
    },

    y: {
      grid: {
        display: false,
      },
      ticks: {
        padding: 12,
        font: {
          size: 12,
        },
      },
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


const gdpStackedOpts = {
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
      stacked: true,
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
      stacked: true,
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
// Stat card
// ─────────────────────────────────────────────────────────
function StatCard({ icon, label, value }) {
  const up = value >= 0

  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>

      <div className="stat-info">
        <span className={up ? 'stat-up' : 'stat-down'}>
          {up ? '▲' : '▼'} {Math.abs(value)}%
        </span>

        <span className="stat-label">{label}</span>
      </div>
    </div>
  )
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
// Main Dashboard
// ─────────────────────────────────────────────────────────
export default function Dashboard() {
  const [stats, setStats] = useState({})
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

        setStats(statsRes.data)
        setRsui(rsRes.data.data)
        setInsights(insRes.data.insights)

        const chartNames = [
  'gdp-sector-trend',
  'gdp-shortrun-effect',
  'gdp-longrun-effect'
]

const chartResults = await Promise.all(
  chartNames.map((c) =>
    api.get(`/api/gdp/charts/${c}`)
  )
)

const chartData = {}

chartNames.forEach((name, i) => {
  chartData[name] = chartResults[i].data.data
})

setCharts(chartData)

        setLoading(false)
      } catch (err) {
        console.error('Dashboard API error', err)
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  if (loading) {
    return <div className="dashboard">Loading dashboard...</div>
  }

  const statItems = [
    { icon: '📊', label: 'GDP', value: stats.gdp_change || 0 },
    { icon: '💰', label: 'Wages', value: stats.wages_change || 0 },
    { icon: '🌾', label: 'Agriculture', value: stats.agriculture_change || 0 },
    { icon: '👥', label: 'Unemployment', value: stats.unemployment_change || 0 },
    {
      icon: '🛒',
      label: 'Consumption',
      value: stats.personal_consumption_change || 0,
    },
    {
      icon: '🏛️',
      label: 'Govt. Expenditure',
      value: stats.govt_expenditure_change || 0,
    },
  ]

  const rsuiLine = {
    labels: rsui.map((r) => r.year),
    datasets: [
      {
        data: rsui.map((r) => r.value),
        borderColor: '#e8614a',
        backgroundColor: 'rgba(232,97,74,.12)',
        fill: true,
        tension: 0.4,
      },
    ],
  }

  return (
    <div className="dashboard">

      {/* Charts */}
      <div className="charts-grid">

        {Array.isArray(charts['gdp-sector-trend']) &&
            charts['gdp-sector-trend'].length > 0 && (
              <ChartCard title="GDP Growth Trend by Sector" height={420}>
                <Line
                  data={gdpTrendDataset(charts['gdp-sector-trend'])}
                  options={gdpTrendOpts}
                />
              </ChartCard>
            )}

       {Array.isArray(charts['gdp-sector-trend']) &&
          charts['gdp-sector-trend'].length > 0 && (
            <ChartCard title="GDP Growth by Sector (Stacked Column)" height={420}>
              <Bar
                data={gdpStackedDataset(charts['gdp-sector-trend'])}
                options={gdpStackedOpts}
              />
            </ChartCard>
          )}

          {charts['gdp-shortrun-effect'] && (
            <ChartCard title="GDP Short-Run Effect on RSUI">
              <Bar data={barDataset(charts['gdp-shortrun-effect'])} options={barOpts} />
            </ChartCard>
          )}

  {charts['gdp-longrun-effect'] && (
        <ChartCard title="GDP Long-Run Effect on RSUI">
          <Bar data={barDataset(charts['gdp-longrun-effect'])} options={barOpts} />
        </ChartCard>
      )}

      </div>

      {/* RSUI Trend */}
      <div className="rsui-card">
        <h3 className="chart-title">Overall RSUI Trend</h3>

        <div style={{ height: 220 }}>
          <Line data={rsuiLine} options={lineOpts} />
        </div>
      </div>

      {/* Insights */}
      <div className="insights-section">
        {insights.map((ins) => (
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
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
  'pce',
  //'gdp-sector',
  //'unemployment_age',
  //'wages_sector',
  //'unemployment_education',
  //'agriculture',
]

const chartResults = await Promise.all(
  chartNames.map((c) =>
    api.get(`/api/dashboard/charts/${c}`)
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

      {/* Stats */}
      <div className="stat-strip">
        {statItems.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      {/* Charts */}
      <div className="charts-grid">

        {charts.pce && (
          <ChartCard title="Personal Consumption Expenditure over Time">
            <Bar data={barDataset(charts.pce)} options={barOpts} />
          </ChartCard>
        )}

       {charts['gdp-sector'] && (
          <ChartCard title="GDP sector impact on RSUI">
            <Bar data={barDataset(charts['gdp-sector'])} options={barOpts} />
          </ChartCard>
        )}

        {charts.unemployment_age && (
          <ChartCard title="Unemployment age impact">
            <Bar data={barDataset(charts.unemployment_age)} options={barOpts} />
          </ChartCard>
        )}

        {charts.wages_sector && (
          <ChartCard title="Wages sector impact">
            <Bar data={barDataset(charts.wages_sector)} options={barOpts} />
          </ChartCard>
        )}

        {charts.unemployment_education && (
          <ChartCard title="Unemployment education impact">
            <Bar
              data={barDataset(charts.unemployment_education)}
              options={barOpts}
            />
          </ChartCard>
        )}

        {charts.agriculture && (
          <ChartCard title="Agriculture impact">
            <Bar data={barDataset(charts.agriculture)} options={barOpts} />
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
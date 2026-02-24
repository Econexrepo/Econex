import { useEffect, useState, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale,
  BarElement, LineElement, PointElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'
import api from '../api/axios'
import './Dashboard.css'

ChartJS.register(
  CategoryScale, LinearScale,
  BarElement, LineElement, PointElement,
  Title, Tooltip, Legend, Filler
)

// ── Colour helpers ─────────────────────────────────────────────────────────────
const BAR_COLORS = [
  '#7c6ff7','#e8614a','#10b981','#f59e0b','#3b82f6','#ec4899',
]

function barDataset(data, label = 'Impact strength') {
  return {
    labels: data.map((d) => d.label),
    datasets: [{
      label,
      data: data.map((d) => d.value),
      backgroundColor: data.map((_, i) => BAR_COLORS[i % BAR_COLORS.length]),
      borderRadius: 4,
      barThickness: 16,
    }],
  }
}

const barOpts = (max = 100) => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed.x}` } } },
  scales: {
    x: { max, grid: { color: '#e5e7eb' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    y: { grid: { display: false }, ticks: { color: '#374151', font: { size: 11 } } },
  },
})

const lineOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: '#e5e7eb' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    y: { grid: { color: '#e5e7eb' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
  },
}

// ── Stat card ──────────────────────────────────────────────────────────────────
function StatCard({ icon, label, value }) {
  const up = value >= 0
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div className="stat-info">
        <span className={`stat-value ${up ? 'stat-up' : 'stat-down'}`}>
          {up ? '▲' : '▼'} {Math.abs(value)}%
        </span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  )
}

// ── Chart card ─────────────────────────────────────────────────────────────────
function ChartCard({ title, children, height = 220 }) {
  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div style={{ height }}>
        {children}
      </div>
    </div>
  )
}

// ── Insight card ───────────────────────────────────────────────────────────────
function InsightCard({ icon, title, description, type }) {
  return (
    <div className={`insight-card insight-card--${type}`}>
      <div className="insight-header">
        <span className="insight-icon">{icon}</span>
        <span className="insight-title">{title}</span>
      </div>
      <p className="insight-desc">{description}</p>
    </div>
  )
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
// Dummy data (used while backend isn't connected)
const DUMMY_STATS = {
  gdp_change: -6.8, wages_change: 12.3, agriculture_change: 10.5,
  unemployment_change: 15.1, personal_consumption_change: 15.1, govt_expenditure_change: 6.8,
}

const DUMMY_CHARTS = {
  pce: [
    { label: 'Food & beverages', value: 79.78 },
    { label: 'Transport', value: 23.59 },
    { label: 'Housing', value: 38.0 },
    { label: 'Health', value: 20.61 },
    { label: 'Education', value: 85.04 },
    { label: 'Communication', value: 67.03 },
  ],
  gdp_sector: [
    { label: 'Agriculture', value: 98.0 },
    { label: 'Services', value: 66.0 },
    { label: 'Industry', value: 88.0 },
  ],
  unemployment_age: [
    { label: '15–19', value: 84.79 },
    { label: '20–24', value: 75.28 },
    { label: '25–29', value: 28.45 },
    { label: '30–39', value: 57.03 },
    { label: '40+', value: 21.70 },
  ],
  wages_sector: [
    { label: 'Workers – Agriculture', value: 65.34 },
    { label: 'Workers – Industry', value: 19.26 },
    { label: 'Central Govt. Employees', value: 89.65 },
    { label: 'Workers – Services', value: 40.09 },
  ],
  unemployment_education: [
    { label: 'Grade 5 below', value: 65.34 },
    { label: '6 to 10', value: 19.26 },
    { label: 'GCE O/L', value: 89.85 },
    { label: 'GCE A/L & above', value: 40.09 },
  ],
  agriculture: [
    { label: '15–19', value: 84.78 },
    { label: '20–24', value: 75.28 },
    { label: '25–29', value: 28.45 },
    { label: '30–39', value: 57.03 },
    { label: '40+', value: 21.70 },
  ],
}

const DUMMY_RSUI = [
  { year: 2000, value: 14.2 }, { year: 2001, value: 15.8 }, { year: 2002, value: 18.1 },
  { year: 2003, value: 17.3 }, { year: 2004, value: 19.6 }, { year: 2005, value: 21.2 },
  { year: 2006, value: 22.8 }, { year: 2007, value: 28.4 }, { year: 2008, value: 24.5 },
  { year: 2009, value: 22.1 }, { year: 2010, value: 25.8 }, { year: 2011, value: 28.2 },
  { year: 2012, value: 29.6 }, { year: 2013, value: 31.4 }, { year: 2014, value: 33.8 },
  { year: 2015, value: 32.1 }, { year: 2016, value: 35.7 },
]

const DUMMY_INSIGHTS = [
  { id: 'ins-1', type: 'danger',  icon: '⚠️', title: 'High Risk Alert',
    description: 'Employment sector showing critical impact (72.8) with rising unemployment rates. Immediate intervention recommended.' },
  { id: 'ins-2', type: 'warning', icon: '📈', title: 'Wage Pressure Increasing',
    description: 'Wages impact index at 68.4 with 12.3% increase. Monitor closely for potential social unrest triggers.' },
  { id: 'ins-3', type: 'success', icon: '🌾', title: 'Agriculture Sector Stable',
    description: 'Agricultural impact at moderate level (54.2). Seasonal variations expected in Q2–Q3 period.' },
  { id: 'ins-4', type: 'info',    icon: '🛒', title: 'Consumption Patterns Shifting',
    description: 'Personal consumption expenditure impact at 61.9. Consumer confidence declining, watch for cascading effects.' },
]

export default function Dashboard() {
  const [stats,    setStats]    = useState(DUMMY_STATS)
  const [charts,   setCharts]   = useState(DUMMY_CHARTS)
  const [rsui,     setRsui]     = useState(DUMMY_RSUI)
  const [insights, setInsights] = useState(DUMMY_INSIGHTS)

  // Attempt to load from API; silently fall back to dummy data
  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, rsRes, insRes] = await Promise.all([
          api.get('/api/dashboard/stats'),
          api.get('/api/dashboard/rsui-trend'),
          api.get('/api/dashboard/insights'),
        ])
        setStats(statsRes.data)
        setRsui(rsRes.data.data)
        setInsights(insRes.data.insights)

        const chartNames = ['pce','gdp_sector','unemployment_age','wages_sector','unemployment_education','agriculture']
        const chartResults = await Promise.all(
          chartNames.map((n) => api.get(`/api/dashboard/charts/${n}`))
        )
        const newCharts = {}
        chartNames.forEach((n, i) => { newCharts[n] = chartResults[i].data.data })
        setCharts(newCharts)
      } catch { /* use dummy data */ }
    }
    load()
  }, [])

  const statItems = [
    { icon: '📊', label: 'GDP',                  value: stats.gdp_change },
    { icon: '💰', label: 'Wages',                value: stats.wages_change },
    { icon: '🌾', label: 'Agriculture',          value: stats.agriculture_change },
    { icon: '👥', label: 'Unemployment',         value: stats.unemployment_change },
    { icon: '🛒', label: 'Personal Consumption', value: stats.personal_consumption_change },
    { icon: '🏛️', label: 'Govt. Expenditure',   value: stats.govt_expenditure_change },
  ]

  const rsLine = {
    labels: rsui.map((r) => r.year),
    datasets: [{
      data: rsui.map((r) => r.value),
      borderColor: '#e8614a',
      backgroundColor: 'rgba(232,97,74,.12)',
      fill: true,
      tension: 0.4,
      pointRadius: 3,
    }],
  }

  return (
    <div className="dashboard">
      {/* Stat strip */}
      <div className="stat-strip">
        {statItems.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      {/* Charts grid */}
      <div className="charts-grid">
        <ChartCard title="PCE impact on RSUI" height={220}>
          <Bar data={barDataset(charts.pce)} options={barOpts(100)} />
        </ChartCard>

        <ChartCard title="GDP sector impact on RSUI" height={160}>
          <Bar data={barDataset(charts.gdp_sector)} options={barOpts(100)} />
        </ChartCard>

        <ChartCard title="Unemployment age level impact on RSUI" height={220}>
          <Bar data={barDataset(charts.unemployment_age)} options={barOpts(100)} />
        </ChartCard>

        <ChartCard title="Wages sector impact on RSUI" height={220}>
          <Bar data={barDataset(charts.wages_sector)} options={barOpts(100)} />
        </ChartCard>

        <ChartCard title="Unemployment educational level impact on RSUI" height={200}>
          <Bar data={barDataset(charts.unemployment_education)} options={barOpts(100)} />
        </ChartCard>

        <ChartCard title="Agriculture impact on RSUI" height={220}>
          <Bar data={barDataset(charts.agriculture)} options={barOpts(100)} />
        </ChartCard>
      </div>

      {/* RSUI Trend */}
      <div className="rsui-card">
        <h3 className="chart-title">Overall RSUI Trend</h3>
        <p className="chart-sub">Composite social unrest index over time</p>
        <div style={{ height: 220 }}>
          <Line data={rsLine} options={lineOpts} />
        </div>
      </div>

      {/* Insights */}
      <div className="insights-section">
        <div className="insights-header">
          <span className="insights-bulb">💡</span>
          <div>
            <h3 className="insights-title">Key Insights &amp; Predictions</h3>
            <p className="insights-sub">AI-generated analysis based on current trends</p>
          </div>
        </div>
        <div className="insights-grid">
          {insights.map((ins) => <InsightCard key={ins.id} {...ins} />)}
        </div>
      </div>
    </div>
  )
}

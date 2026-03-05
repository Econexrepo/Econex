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
import { Bar, Line, Doughnut } from 'react-chartjs-2'
import { Chart } from "react-chartjs-2"
import { MatrixController, MatrixElement } from "chartjs-chart-matrix";
import { ArcElement } from 'chart.js'
import api from '../api/axios'
import './Dashboard.css'


ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
  Filler,
  MatrixController,
  MatrixElement
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

const PIE_COLORS = [
  "#6366F1",
  "#F97316",
  "#10B981",
  "#F59E0B",
  "#3B82F6",
  "#EC4899",
  "#14B8A6",
  "#E11D48",
  "#8B5CF6",
  "#22C55E",
  "#06B6D4",
  "#F43F5E",
  "#84CC16",
  "#FACC15",
  "#A855F7",
  "#0EA5E9"
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

function lineDataset(data) {
  return {
    labels: data.map((d) => d.year),
    datasets: [
      {
        data: data.map((d) => d.value),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.15)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
      },
    ],
  }
}

function donutDataset(data) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        data: data.map((d) => d.value),
        backgroundColor: data.map(
          (_, i) => PIE_COLORS[i % PIE_COLORS.length]
        ),
        borderWidth: 0,
      },
    ],
  }
}

function heatmapDataset(data) {

  const matrix = []

  data.forEach((d, rowIndex) => {

    matrix.push({
      x: 0,
      y: rowIndex,
      v: Number(d.short_run)
    })

    matrix.push({
      x: 1,
      y: rowIndex,
      v: Number(d.long_run)
    })

  })

  return {
    datasets: [
      {
        label: "ARDL Impact",
        data: matrix,

        backgroundColor(ctx) {

          const v = ctx.raw.v

          if (!v) return "#f3f4f6"

          if (v > 0)
            return `rgba(34,197,94,${Math.min(Math.abs(v)*200,1)})`

          return `rgba(239,68,68,${Math.min(Math.abs(v)*200,1)})`
        },

        width: ({ chart }) =>
          (chart.chartArea || {}).width / 2 - 10,

        height: ({ chart }) =>
          (chart.chartArea || {}).height / data.length - 6
      }
    ]
  }
}

const barOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,

  layout: {
    padding: 15
  },

  plugins: {
    legend: { display: false }
  },

  scales: {
    x: {
      grid: { color: '#e5e7eb' },
      ticks: {
        callback: (value) =>
          (value / 1000000).toFixed(1) + "M"
      }
    },

    y: {
      grid: { display: false },
      ticks: {
        font: {
          size: 12
        }
      }
    }
  }
}

const lineOpts = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) =>
          new Intl.NumberFormat().format(ctx.raw)
      }
    }
  },

  scales: {
    x: {
      grid: { display: false },
      ticks: {
        padding: 8,
        maxRotation: 0,
        autoSkip: true,
        maxTicksLimit: 8
      }
    },

    y: {
      grid: { color: '#e5e7eb' },
      ticks: {
        padding: 8,
        callback: (value) =>
          (value / 1000000).toFixed(1) + "M"
      }
    }
  }
}

const lineRateOpts = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) =>
          ctx.raw.toFixed(2) + "%"
      }
    }
  },

  scales: {
    x: {
      grid: { display: false },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 8
      }
    },

    y: {
      grid: { color: '#e5e7eb' },
      ticks: {
        callback: (v) => v + "%"
      }
    }
  }
}

const volatilityOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,

  layout: {
    padding: 15
  },

  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => ctx.raw.toFixed(2) + "%"
      }
    }
  },

  scales: {
    x: {
      grid: { color: "#e5e7eb" },
      title: {
        display: true,
        text: "Growth Rate Volatility (Std Dev %)"
      },
      ticks: {
        callback: (value) => value.toFixed(1) + "%"
      }
    },

    y: {
      grid: { display: false },
      ticks: {
        font: {
          size: 12
        }
      }
    }
  }
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

function PceSummaryCard({ value }) {
  const up = value >= 0

  return (
    <div className="pce-summary-card">
      <div className="pce-icon">🛒</div>

      <h3 className="pce-title">PCE Change</h3>

      <div className={`pce-value ${up ? "stat-up" : "stat-down"}`}>
        {up ? "▲" : "▼"} {Math.abs(value).toFixed(2)}%
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
  "pce-growth-value",
  "pce-growth-rate",
  "pce-share",
  "pce-volatility",
  "ardl-impact"
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

        {charts.pce && (
          <ChartCard title="Personal Consumption Expenditure over Time">
            <Bar data={barDataset(charts.pce)} options={barOpts} />
          </ChartCard>
        )}


        {charts['pce-growth-value'] && (
          <ChartCard title="PCE Growth Value (Absolute Change)">
            <Line
                data={lineDataset(charts['pce-growth-value'])}
                options={lineOpts}
            />
          </ChartCard>
        )}

        {charts['pce-growth-rate'] && (
          <ChartCard title="PCE Growth Rate (%)">
            <Line
              data={lineDataset(charts['pce-growth-rate'], '#10b981')}
              options={lineRateOpts}
/>
          </ChartCard>
        )}

        {charts['pce-share'] && (
          <ChartCard title="PCE Category Share" height={450}>
            <Doughnut
              data={donutDataset(charts['pce-share'])}
              options={{
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "right",
                    labels: {
                      boxWidth: 18,
                      padding: 15
                    }
                  }
                }
              }}
            />
  
          </ChartCard>
        )}

        {charts["pce-volatility"] && (
          <ChartCard title="Consumption Volatility by Sector">
            <Bar
            data={barDataset(charts["pce-volatility"])}
            options={volatilityOpts}
            />
          </ChartCard>
        )}

      <PceSummaryCard value={stats.personal_consumption_change || 0} />

          {charts["ardl-impact"] && (
      <ChartCard title="ARDL Impact Heatmap" height={350}>
              <Chart
        type="matrix"
        data={heatmapDataset(charts["ardl-impact"])}
        options={{
          maintainAspectRatio:false,

          plugins:{
            legend:{display:false}
          },

                  scales: {

          x: {
            type: "linear",
            min: -0.5,
            max: 1.5,

            ticks: {
              stepSize: 1,
              callback: (value) => {
                if (value === 0) return "Short Run"
                if (value === 1) return "Long Run"
                return ""
              }
            },

            grid: { display: false }
          },

          y: {
            type: "linear",
            min: -0.5,
            max: charts["ardl-impact"].length - 0.5,

            ticks: {
              callback: (value) =>
                charts["ardl-impact"][value]?.variable || ""
            },

            grid: { display: false }
          }

        }
        }}
      />
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
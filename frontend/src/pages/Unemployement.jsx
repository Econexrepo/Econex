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
import { useQueries } from '@tanstack/react-query'
import api from '../api/axios'
import { useDashboardStats, useRSUITrend } from '../hooks/useSharedData'
import { unemploymentInsights } from '../data/insights'
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


const unemploymentTrendOpts = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: {
      display: true,
      position: "bottom",
      labels: {
        boxWidth: 12,
        padding: 12,
        font: { size: 11 }
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(1)}%`
      }
    }
  },

  scales: {
    x: {
      grid: { display: false },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 10
      },
      title: {
        display: true,
        text: "Year"
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: "#e5e7eb" },
      ticks: {
        callback: (v) => `${v}%`
      },
      title: {
        display: true,
        text: "Unemployment Rate (%)"
      }
    }
  }
}

const totalUnemploymentTrendOpts = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: {
      display: true,
      position: "bottom",
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(1)}%`
      }
    }
  },

  scales: {
    x: {
      grid: { display: false },
      title: {
        display: true,
        text: "Year"
      },
      ticks: {
        autoSkip: true,
        maxTicksLimit: 10
      }
    },
    y: {
      beginAtZero: false, // better for trend readability
      grid: { color: "#e5e7eb" },
      title: {
        display: true,
        text: "Unemployment Rate (%)"
      },
      ticks: {
        callback: (v) => `${v}%`
      }
    }
  }
}


const longRunEffectOpts = {
  indexAxis: "y",
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
      grid: { color: "#e5e7eb" },
      title: {
        display: true,
        text: "Long-run effect (coefficient)",
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
  indexAxis: "y",
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
      grid: { color: "#e5e7eb" },
      title: {
        display: true,
        text: "Short-run effect (coefficient)",
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


function totalUnemploymentLineDataset(data) {
  return {
    labels: data.map((d) => d.year),
    datasets: [
      {
        label: "Total Unemployment",
        data: data.map((d) => d.value),
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.12)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      },
    ],
  }
}

function longRunEffectBarDataset(data) {
  // data: [{ label, value, n_obs, aic, bic }]
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: "Long-run effect",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.value >= 0 ? "rgba(34,197,94,0.85)" : "rgba(239,68,68,0.85)"
        ),
        borderColor: data.map((d) =>
          d.value >= 0 ? "rgba(22,163,74,1)" : "rgba(220,38,38,1)"
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}

function shortRunEffectBarDataset(data) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: "Short-run ARDL Coefficients",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.is_significant ? "rgba(34,197,94,0.85)" : "rgba(239,68,68,0.85)"
        ),
        borderColor: data.map((d) =>
          d.is_significant ? "rgba(22,163,74,1)" : "rgba(220,38,38,1)"
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}

function longRunEducationEffectBarDataset(data) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: "Long-run Effect",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.value >= 0 ? "rgba(34,197,94,0.85)" : "rgba(239,68,68,0.85)"
        ),
        borderColor: data.map((d) =>
          d.value >= 0 ? "rgba(22,163,74,1)" : "rgba(220,38,38,1)"
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}

function shortRunEducationEffectBarDataset(data) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        label: "Short-run Effect",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          d.is_significant ? "rgba(34,197,94,0.85)" : "rgba(239,68,68,0.85)"
        ),
        borderColor: data.map((d) =>
          d.is_significant ? "rgba(22,163,74,1)" : "rgba(220,38,38,1)"
        ),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }
}


function unemploymentAgeTrendDataset(data) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  
  // Unique sorted years
  const years = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)

  // Unique categories (age groups)
  const categories = [...new Set(data.map((d) => d.category))]

  // Color palette for multiple lines
  const LINE_COLORS = [
    "#3b82f6", // blue
    "#10b981", // green
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // violet
    "#06b6d4", // cyan
    "#ec4899", // pink
    "#84cc16", // lime
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
  const { data: stats = {}, isLoading: statsLoading } = useDashboardStats()
  const { data: rsuiData, isLoading: rsuiLoading } = useRSUITrend()
  const rsui = rsuiData?.data || []

  const chartNames = [
    'unemployment-age-trend',
    'unemployment-education-trend',
    'total-unemployment-trend',
    'unemployment-age-longrun',
    'ardl-short-significance',
    'long-run-education-effect',
    'short-run-education-effect',
    'total-unemployment-longrun',
  ]

  const chartQueries = useQueries({
    queries: chartNames.map(name => ({
      queryKey: ['unemployment', 'chart', name],
      queryFn: () => api.get(`/api/unemployment/charts/${name}`).then(res => res.data.data),
    })),
  })

  const chartsLoading = chartQueries.some(q => q.isLoading)

  const charts = {}
  chartNames.forEach((name, i) => {
    charts[name] = chartQueries[i].data || null
  })

  const loading = statsLoading || rsuiLoading || chartsLoading

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

        {charts["unemployment-age-trend"] && (
          <ChartCard title="Unemployment by Age Group Trend" height={420}>
            <Line
              data={unemploymentAgeTrendDataset(charts["unemployment-age-trend"])}
              options={unemploymentTrendOpts}
            />
          </ChartCard>
        )}

        {charts["unemployment-education-trend"] && (
          <ChartCard title="unemployment-education-trend" height={420}>
            <Line
              data={unemploymentAgeTrendDataset(charts["unemployment-education-trend"])}
              options={unemploymentTrendOpts}
            />
          </ChartCard>
        )}

       {charts["total-unemployment-trend"] && (
          <ChartCard title="Total Unemployment Trend" height={380}>
            <Line
              data={totalUnemploymentLineDataset(charts["total-unemployment-trend"])}
              options={totalUnemploymentTrendOpts}
            />
          </ChartCard>
        )}

        {charts["unemployment-age-longrun"]?.length > 0 && (
          <ChartCard title="Long-run ARDL Effect by Age Group" height={360} className="chart-card--full">
            <Bar
              data={longRunEffectBarDataset(charts["unemployment-age-longrun"])}
              options={longRunEffectOpts}
            />
          </ChartCard>
        )}

        {charts["ardl-short-significance"]?.length > 0 && (
          <ChartCard title="Short-run ARDL Effect by Age Group" height={360} className="chart-card--full">
            <Bar
              data={shortRunEffectBarDataset(charts["ardl-short-significance"])}
              options={shortRunEffectOpts}
            />
          </ChartCard>
        )}

        {charts["long-run-education-effect"]?.length > 0 && (
          <ChartCard title="Long-run ARDL Effect by Education Level" height={360} className="chart-card--full">
            <Bar
              data={longRunEducationEffectBarDataset(charts["long-run-education-effect"])}
              options={longRunEffectOpts}
            />
          </ChartCard>
        )}

        {charts["short-run-education-effect"]?.length > 0 && (
          <ChartCard title="Short-run ARDL Effect by Education Level" height={360} className="chart-card--full">
            <Bar
              data={shortRunEducationEffectBarDataset(charts["short-run-education-effect"])}
              options={shortRunEffectOpts}
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
        {unemploymentInsights.map((ins) => (
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
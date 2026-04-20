import React, { useEffect, useMemo, useState } from 'react'
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
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'
import { useDashboardStats, useRSUITrend } from '../hooks/useSharedData'
import { agricultureInsights } from '../data/insights'
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

const BAR_COLORS = [
  '#7c6ff7',
  '#e8614a',
  '#10b981',
  '#f59e0b',
  '#3b82f6',
  '#ec4899',
]

function shortenLabel(label, max = 55) {
  const text = String(label || '')
  return text.length > max ? `${text.slice(0, max)}...` : text
}

function barDataset(data = []) {
  return {
    labels: data.map((d) => d.label),
    datasets: [
      {
        data: data.map((d) => d.value),
        backgroundColor: data.map((_, i) => BAR_COLORS[i % BAR_COLORS.length]),
        borderRadius: 6,
        categoryPercentage: 0.6,
        barPercentage: 0.7,
      },
    ],
  }
}

function faoStackedAreaDataset(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { labels: [], datasets: [] }
  }

  const years = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)
  const categories = [...new Set(data.map((d) => d.category))]

  const COLORS = [
    'rgba(59,130,246,0.55)',
    'rgba(16,185,129,0.55)',
    'rgba(245,158,11,0.55)',
    'rgba(239,68,68,0.55)',
    'rgba(139,92,246,0.55)',
  ]

  const BORDER_COLORS = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
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
      borderColor: BORDER_COLORS[idx % BORDER_COLORS.length],
      backgroundColor: COLORS[idx % COLORS.length],
      fill: true,
      tension: 0.25,
      pointRadius: 2,
      pointHoverRadius: 4,
      borderWidth: 2,
      stack: 'fao-stack',
    }
  })

  return {
    labels: years,
    datasets,
  }
}

function multiLineDataset(data = []) {
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

function agriEffectDataset(data = []) {
  return {
    labels: data.map((d) => shortenLabel(d.label)),
    datasets: [
      {
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) =>
          Number(d.value) >= 0 ? '#10b981' : '#ef4444'
        ),
        borderRadius: 6,
        categoryPercentage: 0.7,
        barPercentage: 0.8,
      },
    ],
  }
}

function agriShortRunDataset(data = []) {
  return {
    labels: data.map((d) => shortenLabel(d.label)),
    datasets: [
      {
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) => {
          if (d.is_significant) {
            return Number(d.value) >= 0 ? '#10b981' : '#ef4444'
          }
          return '#cbd5e1'
        }),
        borderRadius: 6,
        categoryPercentage: 0.7,
        barPercentage: 0.8,
      },
    ],
  }
}

function buildHeatmapMatrix(data = []) {
  if (!Array.isArray(data) || data.length === 0) {
    return { years: [], items: [], matrix: [], min: 0, max: 0 }
  }

  const allYears = [...new Set(data.map((d) => Number(d.year)))].sort((a, b) => a - b)
  const years = allYears.slice(-12)
  const items = [...new Set(data.map((d) => d.item))]

  const filteredData = data.filter((d) => years.includes(Number(d.year)))

  const values = filteredData
    .map((d) => Number(d.value))
    .filter((v) => Number.isFinite(v))

  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0

  const lookup = new Map(
    filteredData.map((d) => [`${d.item}__${Number(d.year)}`, Number(d.value)])
  )

  const matrix = items.map((item) => ({
    item,
    values: years.map((year) => {
      const val = lookup.get(`${item}__${year}`)
      return Number.isFinite(val) ? val : null
    }),
  }))

  return { years, items, matrix, min, max }
}

function getHeatColor(value, min, max) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '#f3f4f6'
  }

  if (max === min) {
    return 'rgba(59,130,246,0.6)'
  }

  const ratio = (value - min) / (max - min)
  const alpha = 0.15 + ratio * 0.75

  return `rgba(59,130,246,${alpha})`
}

const lineOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

const barOpts = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
  },
  scales: {
    x: {
      grid: {
        color: '#e5e7eb',
      },
    },
    y: {
      grid: {
        display: false,
      },
    },
  },
}

function agriEffectOpts(data = []) {
  return {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          title: (items) => {
            const idx = items[0]?.dataIndex
            return idx !== undefined ? data[idx]?.label || '' : ''
          },
          label: (ctx) => `Effect: ${Number(ctx.raw).toFixed(4)}`,
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: '#e5e7eb',
        },
        title: {
          display: true,
          text: 'Effect Value',
        },
      },
      y: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
          },
        },
      },
    },
  }
}

function agriShortRunOpts(data = []) {
  return {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          title: (items) => {
            const idx = items[0]?.dataIndex
            return idx !== undefined ? data[idx]?.label || '' : ''
          },
          label: (ctx) => `Effect: ${Number(ctx.raw).toFixed(4)}`,
          afterLabel: (ctx) => {
            const row = data[ctx.dataIndex]
            return row ? `p-value: ${Number(row.p_value).toFixed(4)}` : ''
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: '#e5e7eb',
        },
        title: {
          display: true,
          text: 'Short-Run Effect Value',
        },
      },
      y: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
          },
        },
      },
    },
  }
}

const faoStackedAreaOpts = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
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
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(2)}`,
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
        text: 'Value',
      },
    },
  },
}

const multiLineOpts = {
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
        label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.raw).toFixed(2)}`,
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
        text: 'Value',
      },
    },
  },
}

function ChartCard({ title, children, height = 220 }) {
  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div style={{ height }}>{children}</div>
    </div>
  )
}

function HeatmapCard({ title, data, height = 320 }) {
  const { years, matrix, min, max } = buildHeatmapMatrix(data)

  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>

      <div
        style={{
          height,
          overflowX: 'auto',
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `160px repeat(${years.length}, 34px)`,
            gap: '6px',
            alignItems: 'center',
            minWidth: 'max-content',
          }}
        >
          <div></div>

          {years.map((year) => (
            <div
              key={year}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textAlign: 'center',
                color: '#374151',
                writingMode: 'vertical-rl',
                transform: 'rotate(180deg)',
                height: '48px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {year}
            </div>
          ))}

          {matrix.map((row) => (
            <React.Fragment key={row.item}>
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 500,
                  color: '#111827',
                  paddingRight: '8px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                title={row.item}
              >
                {row.item}
              </div>

              {row.values.map((value, idx) => (
                <div
                  key={`${row.item}-${years[idx]}`}
                  title={`${row.item} | ${years[idx]}: ${
                    value !== null ? Number(value).toFixed(2) : 'N/A'
                  }`}
                  style={{
                    width: '34px',
                    height: '28px',
                    borderRadius: '6px',
                    background: getHeatColor(value, min, max),
                  }}
                />
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [selectedAgriUnit, setSelectedAgriUnit] = useState('')
  const [selectedShortRunUnit, setSelectedShortRunUnit] = useState('')

  useDashboardStats()

  const { data: rsuiData, isLoading: rsuiLoading } = useRSUITrend()
  const rsui = rsuiData?.data || []

  const { data: agriEffects = [], isLoading: agriEffectsLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'agri-effect-only'],
    queryFn: () => api.get('/api/agriculture/charts/agri-effect-only?horizon=long_run&top_n=50').then(res => res.data.data || []),
  })

  const { data: agriShortRun = [], isLoading: agriShortRunLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'ardl-short-significance'],
    queryFn: () => api.get('/api/agriculture/charts/ardl-short-significance').then(res => res.data.data || []),
  })

  const { data: faoLatestTop = [], isLoading: faoLatestTopLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'fao-latest-top-items'],
    queryFn: () => api.get('/api/agriculture/charts/fao-latest-top-items?top_n=5').then(res => res.data.data || []),
  })

  const { data: faoMultilineTrend, isLoading: faoMultilineLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'fao-multiline-trend'],
    queryFn: () => api.get('/api/agriculture/charts/fao-multiline-trend').then(res => res.data.data),
  })

  const { data: faoArea = [], isLoading: faoAreaLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'fao-multiline-trend-top5'],
    queryFn: () => api.get('/api/agriculture/charts/fao-multiline-trend?top_n=5').then(res => res.data.data || []),
  })

  const { data: faoHeatmap = [], isLoading: faoHeatmapLoading } = useQuery({
    queryKey: ['agriculture', 'chart', 'fao-heatmap'],
    queryFn: () => api.get('/api/agriculture/charts/fao-heatmap?top_n=5').then(res => res.data.data || []),
  })

  const loading = rsuiLoading || agriEffectsLoading || agriShortRunLoading || faoLatestTopLoading || faoMultilineLoading || faoAreaLoading || faoHeatmapLoading

  const agriUnitTabs = useMemo(() => {
    const units = agriEffects.map((row) => extractUnitFromLabel(row.label))
    return [...new Set(units)]
  }, [agriEffects])

  const shortRunUnitTabs = useMemo(() => {
    const units = agriShortRun.map((row) => extractUnitFromLabel(row.label))
    return [...new Set(units)]
  }, [agriShortRun])

  useEffect(() => {
    if (!selectedAgriUnit && agriUnitTabs.length > 0) {
      setSelectedAgriUnit(agriUnitTabs[0])
    }
  }, [agriUnitTabs, selectedAgriUnit])

  useEffect(() => {
    if (!selectedShortRunUnit && shortRunUnitTabs.length > 0) {
      setSelectedShortRunUnit(shortRunUnitTabs[0])
    }
  }, [shortRunUnitTabs, selectedShortRunUnit])

  const activeAgriUnit =
    selectedAgriUnit && agriUnitTabs.includes(selectedAgriUnit)
      ? selectedAgriUnit
      : agriUnitTabs[0] || ''

  const activeShortRunUnit =
    selectedShortRunUnit && shortRunUnitTabs.includes(selectedShortRunUnit)
      ? selectedShortRunUnit
      : shortRunUnitTabs[0] || ''

  const filteredAgriEffects = useMemo(() => {
    return agriEffects
      .filter((row) => extractUnitFromLabel(row.label) === activeAgriUnit)
      .map((row) => ({
        ...row,
        label: removeUnitPrefix(row.label),
      }))
  }, [agriEffects, activeAgriUnit])

  const filteredAgriShortRun = useMemo(() => {
    return agriShortRun
      .filter((row) => extractUnitFromLabel(row.label) === activeShortRunUnit)
      .map((row) => ({
        ...row,
        label: removeUnitPrefix(row.label),
      }))
  }, [agriShortRun, activeShortRunUnit])

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
      <div className="charts-grid">
        {Array.isArray(faoMultilineTrend) &&
          faoMultilineTrend.length > 0 && (
            <ChartCard title="Top 5 Agricultural Items Trend Over Time" height={420}>
              <Line
                data={multiLineDataset(faoMultilineTrend)}
                options={multiLineOpts}
              />
            </ChartCard>
          )}

        {Array.isArray(faoArea) && faoArea.length > 0 && (
          <ChartCard title="Top Agricultural Items as a Group Over Time" height={420}>
            <Line
              data={faoStackedAreaDataset(faoArea)}
              options={faoStackedAreaOpts}
            />
          </ChartCard>
        )}

        {Array.isArray(faoHeatmap) && faoHeatmap.length > 0 && (
          <HeatmapCard
            title="Agricultural Item Values by Year"
            data={faoHeatmap}
            height={260}
          />
        )}

        {Array.isArray(faoLatestTop) && faoLatestTop.length > 0 && (
          <ChartCard title="Top Agricultural Items in Latest Year" height={320}>
            <Bar
              data={barDataset(faoLatestTop)}
              options={barOpts}
            />
          </ChartCard>
        )}

        {Array.isArray(agriEffects) && agriEffects.length > 0 && (
          <ChartCard title="Top Long-Run Agricultural Effects" height={420}>
            <Bar
              data={agriEffectDataset(agriEffects)}
              options={agriEffectOpts(agriEffects)}
            />
          </ChartCard>
        )}

        {Array.isArray(agriShortRun) && agriShortRun.length > 0 && (
          <ChartCard title="Short-Run Agricultural Effects" height={420}>
            <Bar
              data={agriShortRunDataset(agriShortRun)}
              options={agriShortRunOpts(agriShortRun)}
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
        {agricultureInsights.map((ins) => (
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
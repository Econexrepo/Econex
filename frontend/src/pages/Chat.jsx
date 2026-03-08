import { useState, useEffect, useRef } from 'react'
import api from '../api/axios'
import './Chat.css'
import { FaTrash } from "react-icons/fa"
import ChartMessage from '../components/ChartMessage'

// ── Utility ─────────────────────────────────────────────────────────────────────
function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)    return `${Math.round(diff)}s ago`
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
  return `${Math.round(diff / 86400)}d ago`
}

// ── Render markdown-ish text (bold, bullets) ─────────────────────────────────
function RenderContent({ content }) {
  const lines = content.split('\n')
  return (
    <div className="message-content">
      {lines.map((line, i) => {
        // Bold: **text**
        const parts = line.split(/\*\*(.*?)\*\*/g)
        const rendered = parts.map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )
        // Bullet
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return <li key={i} className="msg-bullet">{rendered}</li>
        }
        if (line === '') return <br key={i} />
        return <p key={i} className="msg-para">{rendered}</p>
      })}
    </div>
  )
}

// ── Domain registry (mirrors backend DOMAIN_REGISTRY) ────────────────────
// Order matters: more-specific entries must come BEFORE generic ones.
const DOMAIN_MAP = [
  // GDP
  { domain: 'gdp', keywords: ['gdp sector', 'gdp growth', 'sector growth', 'gross domestic product sector', 'gdp chart', 'plot gdp'] },
  // Wages
  { domain: 'wages', keywords: ['wage', 'wages', 'salary', 'real wage', 'wage index', 'wage trend'] },
  // Government expenditure – specific before generic
  { domain: 'gov_expenditure_by_type', keywords: ['government expenditure by type', 'gov expenditure by type', 'expenditure by type', 'government spending by type', 'government expenditure', 'government spending', 'gov expenditure', 'public expenditure', 'capital expenditure', 'recurrent expenditure', 'capital and recurrent', 'exp type', 'expenditure type'] },
  { domain: 'total_expenditure',       keywords: ['total expenditure', 'total government expenditure', 'total government spending', 'total spending'] },
  // PCE
  { domain: 'pce', keywords: ['pce', 'personal consumption', 'consumption expenditure', 'household consumption'] },
  // Unemployment – specific before generic
  { domain: 'unemployment_education', keywords: ['unemployment education', 'unemployment by education', 'educated unemployment', 'education unemployment'] },
  { domain: 'unemployment_age',       keywords: ['unemployment age', 'unemployment by age', 'age unemployment', 'age group unemployment'] },
  { domain: 'total_unemployment',     keywords: ['total unemployment', 'unemployment rate', 'unemployment chart', 'unemployment', 'jobless'] },
  // FAO / Agriculture data
  { domain: 'fao_sl', keywords: ['fao', 'fao data', 'food production', 'crop data', 'agricultural production', 'farming data','agriculture data'] },
  // GDP sector (generic fallback – must be LAST among GDP-related)
  { domain: 'gdp', keywords: ['gdp', 'sector', 'agriculture sector', 'industry sector', 'services sector', 'annual growth', 'growth rate', 'sector trend'] },
]

// Chart-trigger words: message must contain at least ONE of these
const CHART_TRIGGERS = ['chart', 'graph', 'plot', 'visuali', 'show', 'draw', 'trend', 'data']

// GDP subsector shortcodes
const GDP_SUBSECTORS = [
  { code: 'AGR', words: ['agriculture', 'agri', 'farming', 'farm'] },
  { code: 'IND', words: ['industry', 'industrial', 'manufactur'] },
  { code: 'SRV', words: ['service', 'services'] },
]

const PCE_CATEGORIES = [
  'food beverages',
  'food and beverages',
  'clothing footwear',
  'transport',
  'housing utility service',
  'housing and utility service',
  'household equipments services',
  'household equipment services',
  'health',
  'education',
  'recreation entertainment',
  'recreation and entertainment',
  'restaurants hotels',
  'restaurants and hotels',
  'miscellaneous goods services',
  'miscellaneous goods and services',
  'information and communication',
  'communication',
  'expenditure abroad of residents',
  'expanditure abroad of residents',
  'expenditure of non residents',
  'expanditure of non residents',
  'food_beverages',
  'cloathing_footwear',
  'housing_utility_service',
  'household_equipments_services',
  'recreation_entertainment',
  'restaurants_hotels',
  'miscellaneous_goods_services',
  'expenditure_abroad_of_residents',
  'expanditure_abroad_of_residents',
  'expenditure_of_non_residents',
  'expanditure_of_non_residents',
  'clothing and footwear',
]

function extractSinglePceTerm(rawText) {
  let s = rawText
    .toLowerCase()
    .replace(/\+/g, ' ')
    .replace(/[–—]/g, '-')
    .replace(/[^\w\s/-]/g, ' ')

  const beforePce = s.match(/\b(?:show|plot|draw|graph)\s+(.+?)\s+(?:pce|personal consumption|consumption expenditure)\b/i)
  if (beforePce?.[1]) return beforePce[1].trim()

  const afterPce = s.match(/\b(?:pce|personal consumption|consumption expenditure)\s+(.+?)(?:\b(graph|chart|plot|trend|percentage|actual|growth|data)\b|$)/i)
  if (afterPce?.[1]) return afterPce[1].trim()

  s = s
    .replace(/\b(show|plot|draw|graph|chart|trend|data)\b/g, ' ')
    .replace(/\b(pce|personal|consumption|expenditure)\b/g, ' ')
    .replace(/\b(percentage|actual|growth|rate|value|index)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!s || /\b(all|overall|total|by category)\b/.test(s)) return null
  return s
}

function normalizeLookup(s) {
  return (s || '')
    .toLowerCase()
    .replace(/\+/g, ' ')
    .replace(/[_/]/g, ' ')
    .replace(/[–—]/g, '-')
    .replace(/&/g, ' and ')
    .replace(/[^\w\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function pickFromCatalog(rawText, options, maxCount = 1) {
  if (!Array.isArray(options) || options.length === 0) return []
  const textN = normalizeLookup(rawText)
  const stop = new Set([
    'show', 'graph', 'chart', 'plot', 'trend', 'data',
    'pce', 'fao', 'percentage', 'index', 'growth', 'rate',
    'for', 'in', 'of', 'and', 'by', 'among', 'level', 'group',
    'values', 'actual', 'production',
  ])
  const qTokens = textN.split(' ').filter((t) => t && !stop.has(t))
  if (qTokens.length === 0) return []

  const scored = options
    .map((o) => {
      const nameN = normalizeLookup(o.name)
      const codeN = normalizeLookup(o.code)
      const label = `${nameN} ${codeN}`.trim()
      let score = 0
      for (const t of qTokens) {
        if (label.includes(t)) score += 1
      }
      return { item: o, score }
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)

  const out = []
  const seen = new Set()
  for (const s of scored) {
    const key = `${s.item.code}|${s.item.name}`.toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      out.push(s.item)
    }
    if (out.length >= maxCount) break
  }
  return out
}

// Extract year range from text: "2005 to 2020", "2005-2020", "from 2005", "since 2010"
function extractYearRange(t) {
  const rangeRe  = /(\d{4})\s*(?:to|–|-|through)\s*(\d{4})/i
  const fromRe   = /(?:from|since|after|starting|beginning)\s+(\d{4})/i
  const toRe     = /(?:to|until|through|up\s+to|before)\s+(\d{4})/i

  const rangeM = t.match(rangeRe)
  if (rangeM) return { year_from: parseInt(rangeM[1]), year_to: parseInt(rangeM[2]) }

  const fromM = t.match(fromRe)
  const toM   = t.match(toRe)
  if (fromM || toM) {
    return {
      year_from: fromM ? parseInt(fromM[1]) : null,
      year_to:   toM   ? parseInt(toM[1])   : null,
    }
  }
  return { year_from: null, year_to: null }
}

function extractCompareTerms(rawText) {
  const m = rawText.match(/\bcompare\s+(.+?)(?:\s*\(?(?:graph|chart|plot)\)?\s*)?(?:[.?!]|$)/i)
  if (!m) return null
  const segment = m[1]
    .replace(/\b(pce|gdp|wage|wages|index|growth|trend)\b/gi, '')
    .trim()
  const parts = segment
    .split(/\s*(?:,|\/|\bvs\b|\bversus\b|\band\b)\s*/i)
    .map((s) => s.trim())
    .filter(Boolean)
  return parts.length >= 2 ? parts : null
}

function normalizeCompareTerm(term, domain) {
  let cleaned = term
    .replace(/[\u2013\u2014\u2212]/g, '-')
    .replace(/\b(graph|chart|plot|line|bar|area)\b/gi, '')
    .replace(/\b(in|of|for)\s+(a|an|the)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim()

  if (domain === 'unemployment_age') {
    return cleaned
      .replace(/\bunemployment\b/gi, '')
      .replace(/\bage\s*group\b/gi, '')
      .replace(/\bof\s+age\b/gi, '')
      .replace(/\bage\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
  }

  if (domain === 'wages') {
    let out = cleaned
      .replace(/\bwage\s*index\b/gi, '')
      .replace(/\bindex\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
    const t = out.toLowerCase()
    if (/(central).*(govt|government)/i.test(t)) return 'central govt employees'
    if (/(industry|commerce)/i.test(t)) return 'workers in industry and commerce'
    if (/(agri|agriculture|farm)/i.test(t)) return 'workers in agriculture'
    if (/(service|services)/i.test(t)) return 'workers in services'
    if (/(wages?\s+boards?)/i.test(t)) return 'all wages boards trades'
    return out
  }

  if (domain === 'gdp') {
    let out = cleaned
      .replace(/\bgdp\b/gi, '')
      .replace(/\bgrowth(?:\s*rate)?\b/gi, '')
      .replace(/\bsector\b/gi, '')
      .replace(/\bin\s+sri\s+lanka\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
    const t = out.toLowerCase()
    if (/(agri|agriculture|farm)/i.test(t)) return 'agriculture'
    if (/(industry|industrial|manufactur)/i.test(t)) return 'industry'
    if (/(service|services)/i.test(t)) return 'services'
    return out
  }

  if (domain === 'pce') {
    let out = cleaned
      .replace(/\bpce\b/gi, '')
      .replace(/\bpercentage\b/gi, '')
      .replace(/\bconsumption\b/gi, '')
      .replace(/\bexpenditure\b/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
    const t = out.toLowerCase().replace(/&/g, ' and ')
    if (/(clothing).*(footwear)|(footwear).*(clothing)/i.test(t)) return 'clothing and footwear'
    if (/\bcommunication\b/i.test(t)) return 'communication'
    if (/\btransport\b/i.test(t)) return 'transport'
    return out
  }

  if (domain === 'gov_expenditure_by_type') {
    const t = cleaned.toLowerCase()
    if (/\bcapital\b/i.test(t)) return 'capital expenditure'
    if (/\brecurrent\b/i.test(t)) return 'recurrent expenditure'
    return cleaned
  }

  return cleaned
}

function detectGraphRequest(text, domainSubsectors = {}) {
  const t = text.toLowerCase()
  const tNorm = t.replace(/\+/g, ' ')
  const hasAgeRange = /\b\d{1,2}\s*(?:-|–|—|to)\s*\d{1,2}\b|\b\d{1,2}\s*(?:\+|plus)\b/.test(t)

  // Must have a chart-trigger word
  if (!CHART_TRIGGERS.some(kw => t.includes(kw))) return null

  // Find best-matching domain (first match wins)
  let domain = null
  if (t.includes('unemployment') && hasAgeRange) {
    domain = 'unemployment_age'
  } else if (
    t.includes('unemployment') &&
    (t.includes('gce') || t.includes('o/l') || t.includes('a/l') || t.includes('education') || t.includes('educated'))
  ) {
    domain = 'unemployment_education'
  } else if (t.includes('unemployment') && t.includes('age')) {
    domain = 'unemployment_age'
  } else {
    for (const entry of DOMAIN_MAP) {
      if (entry.keywords.some(kw => t.includes(kw))) {
        domain = entry.domain
        break
      }
    }
  }
  if (!domain) return null

  let subsectors = null
  let filters = null

  const liveOptions = domainSubsectors?.[domain] || []

  const terms = extractCompareTerms(text)
  if (!subsectors && terms) {
    if (liveOptions.length > 0) {
      const picked = terms
        .map((term) => pickFromCatalog(term, liveOptions, 1)[0]?.name)
        .filter(Boolean)
      const uniquePicked = Array.from(new Set(picked))
      if (uniquePicked.length >= 2) subsectors = uniquePicked
    }
    if (!subsectors) {
      const normalized = terms
        .map((term) => normalizeCompareTerm(term, domain))
        .filter(Boolean)
      if (normalized.length >= 2) subsectors = normalized
    }
  }

  // Subsector: currently only meaningful for GDP
  let subsector = 'all'
  if (!subsectors && domain === 'gdp') {
    for (const s of GDP_SUBSECTORS) {
      if (s.words.some(w => t.includes(w))) { subsector = s.code; break }
    }
  }
  if (!subsectors && domain === 'gov_expenditure_by_type') {
    if (/\bcapital\b/i.test(t)) subsectors = ['capital expenditure']
    else if (/\brecurrent\b/i.test(t)) subsectors = ['recurrent expenditure']
  }
  if (!subsectors && domain === 'unemployment_education') {
    const wantsCompareEdu = /\b(compare|vs|versus)\b/i.test(text)
    if (wantsCompareEdu && liveOptions.length > 0) {
      subsectors = liveOptions.map((o) => o.name).filter(Boolean)
    } else if (/\bgce\s*a\s*\/?\s*l\b|\ba\s*\/?\s*l\b|advanced level/i.test(t)) {
      subsectors = ['gce a/l']
    } else if (/\bgce\s*o\s*\/?\s*l\b|\bo\s*\/?\s*l\b|ordinary level/i.test(t)) {
      subsectors = ['gce o/l']
    } else {
      const gradeMatch = t.match(/\bgrade\s*(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\b/)
      if (gradeMatch) subsectors = [`grade ${gradeMatch[1]}-${gradeMatch[2]}`]
      else if (liveOptions.length > 0) {
        const pickedEdu = pickFromCatalog(text, liveOptions, 1)
        if (pickedEdu.length > 0) subsectors = [pickedEdu[0].name]
      }
    }
  }
  if (!subsectors && domain === 'unemployment_age') {
    const ageMatches = Array.from(
      t.matchAll(/\b\d{1,2}\s*\+|\b\d{1,2}\s*plus\b|\b\d{1,2}\s*and above\b|\b\d{1,2}\s*and over\b|\b\d{1,2}\s*(?:-|–|—|to)\s*\d{1,2}\b/g)
    ).map((m) => m[0].trim())

    if (ageMatches.length > 0) {
      subsectors = Array.from(
        new Set(
          ageMatches.map((g) =>
            g
              .replace(/(\d{1,2})\s*plus\b/gi, '$1+')
              .replace(/(\d{1,2})\s*(?:and above|and over)\b/gi, '$1+')
              .replace(/[–—]/g, '-')
              .replace(/\s*to\s*/g, '-')
              .replace(/\b(group|years?)\b/gi, '')
              .replace(/\s+/g, ' ')
              .trim()
          )
        )
      )
    }
  }
  if (!subsectors && domain === 'pce') {
    // Keep "show all" behavior as unfiltered.
    if (!/\b(all|overall|total)\b/i.test(t) && !/\bby\s+category\b/i.test(t)) {
      const pickedLive = pickFromCatalog(text, liveOptions, 1)
      if (pickedLive.length > 0) {
        subsectors = [pickedLive[0].name]
      } else {
        const picked = PCE_CATEGORIES.filter((c) => t.includes(c))
        if (picked.length > 0) {
          subsectors = [normalizeCompareTerm(picked[0], 'pce')]
        } else {
          const single = extractSinglePceTerm(text)
          if (single) subsectors = [normalizeCompareTerm(single, 'pce')]
        }
      }
    }
  }
  if (!subsectors && domain === 'wages') {
    const isGenericWageQuery =
      /\b(wage trends?|wage index|overall wages?|all wages?|all categories?|over time)\b/i.test(text) &&
      !/\b(central\b.*\b(govt|government)|industry|commerce|agri|agriculture|farm|services?|wages?\s+boards?)\b/i.test(text)

    if (/\bsectoral\b/i.test(text)) {
      filters = [...(filters || []), 'category_group:Sectoral']
    }

    if (!isGenericWageQuery) {
      if (liveOptions.length > 0) {
        const pickedWage = pickFromCatalog(text, liveOptions, 1)
        if (pickedWage.length > 0) subsectors = [pickedWage[0].name]
      }
      if (!subsectors) {
        const one = normalizeCompareTerm(text, 'wages')
        if (one) subsectors = [one]
      }
    }
  }

  if (domain === 'fao_sl') {
    const faoFilters = []
    if (/\brice\b/.test(tNorm)) {
      faoFilters.push('item_name:Rice')
    }
    const pickedFao = faoFilters.length === 0 ? pickFromCatalog(text, liveOptions, 1) : []
    if (pickedFao.length > 0) {
      faoFilters.push(`item_name:${pickedFao[0].name}`)
    } else if (/\btea\b/.test(tNorm)) {
      faoFilters.push('item_name:Tea')
    }
    if (/\btonnes?\b|\btons?\b/.test(tNorm)) faoFilters.push('unit_name:tonnes')
    if (faoFilters.length > 0) filters = faoFilters
  }

  // Year range
  const { year_from, year_to } = extractYearRange(t)

  // Chart type
  const chartType = t.includes('bar') ? 'bar' : t.includes('area') ? 'area' : 'line'

  // PCE metric variant
  let metric = 'default'
  if (domain === 'pce') {
    if (t.includes('growth rate') || t.includes('growth %')) metric = 'growth_rate'
    else if (t.includes('actual') || t.includes('rs mn'))    metric = 'actual'
    else if (t.includes('growth value'))                     metric = 'growth_value'
  }

  return { domain, subsector, subsectors, filters, year_from, year_to, chartType, metric }
}

function hydrateMessages(rawMessages = []) {
  return (rawMessages || []).map((m, idx) => {
    const type = m.type || m.message_type
    if (type === 'chart') {
      const payload = m.chart_payload || {}
      const chartData = payload.chartData || payload.data || null
      const chartMeta = payload.chartMeta || null
      const imageUrl = m.image_url
        ? (String(m.image_url).startsWith('http') ? m.image_url : `${api.defaults.baseURL}${m.image_url}`)
        : null
      return {
        role: m.role || 'assistant',
        type: 'chart',
        id: m.id || `chart-hist-${idx}-${Date.now()}`,
        caption: m.content || payload.caption || 'Chart generated from data warehouse.',
        chartMeta,
        chartData,
        activeChartType: chartMeta?.chartType || 'line',
        loading: false,
        error: false,
        imageUrl,
        timestamp: m.timestamp || new Date().toISOString(),
      }
    }
    return {
      role: m.role || 'assistant',
      content: m.content || '',
      timestamp: m.timestamp || new Date().toISOString(),
    }
  })
}

async function captureChartImageById(msgId) {
  await new Promise((resolve) => setTimeout(resolve, 120))
  const canvas = document.querySelector(`[data-chart-msg-id="${msgId}"] canvas`)
  if (!canvas) return null
  try {
    return canvas.toDataURL('image/png')
  } catch {
    return null
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────────
function SessionItem({ session, active, onClick, onDelete }) {
  return (
    <button
      className={`session-item${active ? ' session-item--active' : ''}`}
      onClick={onClick}
    >
      <div className="session-header-row">
        <span className="session-title">{session.title}</span>
        <span className="session-time">{timeAgo(session.created_at)}</span>
        <button
          className="session-delete-btn"
          onClick={(e) => onDelete(session.id, e)}
          title="Delete conversation"
        >
          <FaTrash size={11} />
        </button>
      </div>
      <p className="session-preview">{session.preview}</p>
      {session.tag && <span className={`session-tag session-tag--${session.tag.toLowerCase()}`}>{session.tag}</span>}
    </button>
  )
}

// ── Message bubble (text or chart) ─────────────────────────────────────────
function Message({ msg, onChartTypeChange }) {
  const isUser = msg.role === 'user'

  // ── Chart message ───────────────────────────────────────────────────
  if (msg.type === 'chart') {
    const active = msg.activeChartType || 'line'
    return (
      <div className="message-row">
        <div className="msg-avatar msg-avatar--ai">AI</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '82%' }}>
          {msg.caption && (
            <div className="message-bubble">
              <RenderContent content={msg.caption} />
            </div>
          )}
          {/* Chart type toggle */}
          {!msg.loading && !msg.error && msg.chartData && (
            <div className="chart-type-row">
              {['line', 'bar', 'area'].map(t => (
                <button
                  key={t}
                  className={`chart-type-btn${active === t ? ' chart-type-btn--active' : ''}`}
                  onClick={() => onChartTypeChange(msg.id, t)}
                >
                  {t === 'line' ? '📈 Line' : t === 'bar' ? '📊 Bar' : '🌊 Area'}
                </button>
              ))}
            </div>
          )}
          {!msg.loading && !msg.error && !msg.chartData && msg.imageUrl && (
            <div className="message-bubble">
              <img src={msg.imageUrl} alt="Saved chart" style={{ width: '100%', borderRadius: '12px', display: 'block' }} />
            </div>
          )}
          {(msg.loading || msg.error || msg.chartData) && (
            <div data-chart-msg-id={msg.id}>
              <ChartMessage
                chartData={msg.chartData}
                isLoading={msg.loading}
                error={msg.error}
                activeType={active}
              />
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Normal text message ───────────────────────────────────────────────────
  return (
    <div className={`message-row${isUser ? ' message-row--user' : ''}`}>
      {!isUser && <div className="msg-avatar msg-avatar--ai">AI</div>}
      <div className={`message-bubble${isUser ? ' message-bubble--user' : ''}`}>
        {isUser
          ? msg.content
          : <RenderContent content={msg.content} />
        }
      </div>
      {isUser && (
        <div className="msg-avatar msg-avatar--user">
          <span>ME</span>
        </div>
      )}
    </div>
  )
}

// ── Welcome screen ─────────────────────────────────────────────────────────
function WelcomeScreen({ onSuggest }) {
  const suggestions = [
    { icon: '📈', text: 'Show GDP sector growth chart' },
    { icon: '📊', text: 'Compare all sectors under Wages' },
    { icon: '🛒', text: 'Show PCE consumption chart' },
    { icon: '📉', text: 'Show total unemployment chart' },
    { icon: '🎓', text: 'Show unemployment by education chart' },
    { icon: '📊', text: 'Show GDP growth bar chart from 2010 to 2022' },
    { icon: '🌊', text: 'Show wage trends area chart since 2005' },
  ]
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">🧠</div>
      <h2 className="welcome-title">Econex AI</h2>
      <p className="welcome-subtitle">
        Ask about GDP, Wages, PCE, Expenditure, Unemployment and more —
        powered by live warehouse data.
      </p>
      <div className="suggestions-grid">
        {suggestions.map((s, i) => (
          <button key={i} className="suggestion-chip" onClick={() => onSuggest(s.text)}>
            <span className="suggestion-icon">{s.icon}</span>
            <span>{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Main Chat page ──────────────────────────────────────────────────────────────
export default function Chat() {
  const [sessions,  setSessions]  = useState([])
  const [activeId,  setActiveId]  = useState(null)
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [sending,   setSending]   = useState(false)
  const [search,    setSearch]    = useState('')
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [domainSubsectors, setDomainSubsectors] = useState({})
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const activeIdRef = useRef(null)

  const activateSession = (id) => {
    activeIdRef.current = id || null
    setActiveId(id || null)
  }

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load sessions from API on mount
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const { data } = await api.get('/api/chat/sessions')
        setSessions(data)
        if (data.length > 0) {
          activateSession(data[0].id)
          // Load messages for first session
          const { data: sess } = await api.get(`/api/chat/sessions/${data[0].id}`)
          setMessages(hydrateMessages(sess.messages || []))
        }
      } catch (err) {
        setError('Could not connect to Econex backend. Make sure the server is running.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Load dynamic subsector catalogs for intent parsing (reduces hardcoded lists)
  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const domains = ['pce', 'fao_sl', 'wages', 'gdp', 'unemployment_age', 'unemployment_education', 'gov_expenditure_by_type']
        const responses = await Promise.all(
          domains.map((d) => api.get(`/api/graphs/subsectors?domain=${encodeURIComponent(d)}`))
        )
        const next = {}
        for (let i = 0; i < domains.length; i += 1) {
          next[domains[i]] = responses[i]?.data?.subsectors || []
        }
        setDomainSubsectors(next)
      } catch {
        // Keep parser functional with static fallbacks if metadata cannot be loaded.
      }
    }
    loadCatalogs()
  }, [])

  // Load messages for selected session
  const selectSession = async (id) => {
    activateSession(id)
    try {
      const { data } = await api.get(`/api/chat/sessions/${id}`)
      setMessages(hydrateMessages(data.messages || []))
    } catch {
      setMessages([])
    }
  }

  // New session
  const newSession = async () => {
    try {
      const { data } = await api.post('/api/chat/sessions')
      setSessions((prev) => [data, ...prev])
      activateSession(data.id)
      setMessages([])
      inputRef.current?.focus()
    } catch (err) {
      console.error('Failed to create session', err)
    }
  }

  // Delete session
  const deleteSession = async (id, e) => {
    e.stopPropagation()
    try {
      await api.delete(`/api/chat/sessions/${id}`)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeId === id) {
        const remaining = sessions.filter((s) => s.id !== id)
        if (remaining.length > 0) {
          selectSession(remaining[0].id)
        } else {
          activateSession(null)
          setMessages([])
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err)
    }
  }

  // Send message — also checks for chart requests
  const sendMessage = async (overrideText) => {
    const text = (overrideText || input).trim()
    if (!text || sending) return

    const currentSessionId = activeIdRef.current
    if (!currentSessionId) {
      setError('Click + New to start a chat, then send messages in that chat.')
      inputRef.current?.focus()
      return
    }

    setInput('')
    setSending(true)
    setError(null)

    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages((prev) => [...prev, userMsg])

    // ── Check if the user is asking for a chart ───────────────────────────
    const graphRequest = detectGraphRequest(text, domainSubsectors)

    // Human-readable caption builder
    const DOMAIN_LABELS = {
      gdp:                     'GDP Sector Annual Growth Rate',
      wages:                   'Wage Trends',
      gov_expenditure_by_type: 'Government Expenditure by Type',
      total_expenditure:       'Total Government Expenditure',
      pce:                     'Personal Consumption Expenditure',
      unemployment_education:  'Unemployment by Education Level',
      unemployment_age:        'Unemployment by Age Group',
      total_unemployment:      'Total Unemployment Rate',
      fao_sl:                  'FAO Agriculture Data',
    }
    function _chartCaption(req) {
      const label = DOMAIN_LABELS[req.domain] || req.domain
      const subList = Array.isArray(req.subsectors) && req.subsectors.length > 0
        ? ` (${req.subsectors.join(' vs ')})`
        : ''
      const sub   = req.subsector && req.subsector !== 'all' ? ` (${req.subsector})` : subList
      const yrs   = req.year_from || req.year_to
        ? ` ${req.year_from || ''}–${req.year_to || 'latest'}`
        : ''
      return `Here's the **${label}${sub}** chart${yrs} from the data warehouse:`
    }
    if (graphRequest) {
      // Insert a loading chart message immediately
      const chartMsgId = `chart-${Date.now()}`
      const loadingChartMsg = {
        role:            'assistant',
        type:            'chart',
        id:              chartMsgId,
        caption:         _chartCaption(graphRequest),
        chartMeta:       graphRequest,
        chartData:       null,
        activeChartType: graphRequest.chartType || 'line',
        loading:         true,
        error:           false,
        timestamp:       new Date().toISOString(),
      }
      setMessages((prev) => [...prev, loadingChartMsg])
      setSending(false)

      // Fetch the actual chart data
      try {
        const params = new URLSearchParams()
        params.set('domain',    graphRequest.domain)
        if (graphRequest.subsector && graphRequest.subsector !== 'all')
          params.set('subsector', graphRequest.subsector)
        if (Array.isArray(graphRequest.subsectors)) {
          for (const s of graphRequest.subsectors) {
            if (s) params.append('subsectors', s)
          }
        }
        if (Array.isArray(graphRequest.filters)) {
          for (const f of graphRequest.filters) {
            if (f) params.append('filters', f)
          }
        }
        if (graphRequest.year_from) params.set('year_from', graphRequest.year_from)
        if (graphRequest.year_to)   params.set('year_to',   graphRequest.year_to)
        if (graphRequest.chartType) params.set('type',      graphRequest.chartType)
        if (graphRequest.metric && graphRequest.metric !== 'default')
          params.set('metric', graphRequest.metric)

        const url = `/api/graphs/timeseries?${params.toString()}`
        const { data } = await api.get(url)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === chartMsgId
              ? { ...m, chartData: data, loading: false }
              : m
          )
        )

        try {
          const imageDataUrl = await captureChartImageById(chartMsgId)
          const saveBody = {
            session_id: currentSessionId,
            message: text,
            caption: _chartCaption(graphRequest),
            chart_payload: {
              chartMeta: graphRequest,
              chartData: data,
              caption: _chartCaption(graphRequest),
            },
            image_data_url: imageDataUrl,
          }
          const { data: persisted } = await api.post('/api/chat/chart-message', saveBody)
          if (!activeIdRef.current && persisted?.session_id) {
            activateSession(persisted.session_id)
          }
        } catch (saveErr) {
          console.error('Failed to persist chart message', saveErr)
        }
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === chartMsgId
              ? { ...m, loading: false, error: true }
              : m
          )
        )
      }
      // Refresh sidebar
      try {
        const { data: updatedSessions } = await api.get('/api/chat/sessions')
        setSessions(updatedSessions)
      } catch { /* ignore */ }
      inputRef.current?.focus()
      return
    }

    // ── Normal AI text message ─────────────────────────────────────────────
    try {
      const { data } = await api.post('/api/chat/message', {
        session_id: currentSessionId,
        message: text,
      })
      if (!activeIdRef.current && data?.session_id) {
        activateSession(data.session_id)
      }
      const aiMsg = {
        role: 'assistant',
        content: data.content,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, aiMsg])

      // Refresh sessions list to update preview/title
      const { data: updatedSessions } = await api.get('/api/chat/sessions')
      setSessions(updatedSessions)
    } catch (err) {
      const errMsg = err?.response?.data?.detail || 'Error getting response. Please try again.'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `⚠️ ${errMsg}`, timestamp: new Date().toISOString() },
      ])
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  // Chart type toggle — re-fetch from generic timeseries endpoint
  const handleChartTypeChange = async (msgId, newType) => {
    const msg = messages.find(m => m.id === msgId)
    if (!msg) return

    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, activeChartType: newType, loading: true } : m
    ))

    try {
      const req    = msg.chartMeta
      const params = new URLSearchParams()
      params.set('domain', req.domain)
      if (req.subsector && req.subsector !== 'all') params.set('subsector', req.subsector)
      if (Array.isArray(req.subsectors)) {
        for (const s of req.subsectors) {
          if (s) params.append('subsectors', s)
        }
      }
      if (Array.isArray(req.filters)) {
        for (const f of req.filters) {
          if (f) params.append('filters', f)
        }
      }
      if (req.year_from) params.set('year_from', req.year_from)
      if (req.year_to)   params.set('year_to',   req.year_to)
      if (req.metric && req.metric !== 'default') params.set('metric', req.metric)
      params.set('type', newType)

      const { data } = await api.get(`/api/graphs/timeseries?${params.toString()}`)
      setMessages(prev => prev.map(m =>
        m.id === msgId ? { ...m, chartData: data, activeChartType: newType, loading: false } : m
      ))
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === msgId ? { ...m, activeChartType: newType, loading: false } : m
      ))
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const filtered = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.preview?.toLowerCase().includes(search.toLowerCase())
  )

  const activeSession = sessions.find((s) => s.id === activeId)

  if (loading) {
    return (
      <div className="chat-layout chat-loading">
        <div className="loading-spinner" />
        <p>Connecting to Econex AI…</p>
      </div>
    )
  }

  return (
    <div className="chat-layout">
      {/* ── Left panel: sessions list ── */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <h2 className="chat-sidebar-title">Chat History</h2>
          <button className="new-chat-btn" onClick={newSession} title="New chat">＋ New</button>
        </div>

        <div className="chat-search-wrap">
          <input
            className="chat-search"
            type="text"
            placeholder="🔍 Search conversations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="session-list">
          {filtered.length === 0 && (
            <p className="session-empty">No conversations yet.<br />Start a new chat!</p>
          )}
          {filtered.map((s) => (
            <SessionItem
              key={s.id}
              session={s}
              active={s.id === activeId}
              onClick={() => selectSession(s.id)}
              onDelete={deleteSession}
            />
          ))}
        </div>
      </aside>

      {/* ── Right panel: conversation ── */}
      <div className="chat-main">
        <div className="chat-main-header">
          <div className="chat-header-left">
            <h2 className="chat-conv-title">
              {activeSession?.title || 'Econex AI Assistant'}
            </h2>
            {activeSession?.tag && (
              <span className={`header-tag header-tag--${activeSession.tag.toLowerCase()}`}>
                {activeSession.tag}
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="chat-error-banner">
            ⚠️ {error}
          </div>
        )}

        <div className="messages-area">
          {messages.length === 0 && !sending ? (
            <WelcomeScreen onSuggest={(text) => { sendMessage(text) }} />
          ) : (
            messages.map((msg, i) => <Message key={i} msg={msg} onChartTypeChange={handleChartTypeChange} />)
          )}
          {sending && (
            <div className="message-row">
              <div className="msg-avatar msg-avatar--ai">AI</div>
              <div className="message-bubble typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-row">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            placeholder="Ask me anything — e.g. 'What is RSUI?'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={!input.trim() || sending}
            title="Send (Enter)"
          >
            {sending ? '…' : '➤'}
          </button>
        </div>
        <p className="chat-hint">Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}

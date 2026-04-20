export const dashboardInsights = [
  {
    id: "ins-1",
    type: "danger",
    icon: "⚠️",
    title: "High Risk Alert",
    description: "RSUI indicates increasing socio-economic pressure."
  },
  {
    id: "ins-2",
    type: "warning",
    icon: "📈",
    title: "Consumption Volatility",
    description: "Personal consumption categories fluctuating significantly."
  },
  {
    id: "ins-3",
    type: "success",
    icon: "🌾",
    title: "Agriculture Sector Stable",
    description: "Agricultural output stable relative to RSUI baseline."
  }
]

// GDP, Agriculture, Wages, Unemployment all share the same generic insights
export const gdpInsights = dashboardInsights
export const agricultureInsights = dashboardInsights
export const wagesInsights = dashboardInsights
export const unemploymentInsights = dashboardInsights

// Government Expenditure has unique domain-specific insights
export const expenditureInsights = [
  {
    id: "govexp-1",
    type: "warning",
    icon: "💰",
    title: "Government Spending Shift",
    description: "Capital and recurrent expenditure trends can signal changing public investment priorities."
  },
  {
    id: "govexp-2",
    type: "danger",
    icon: "📉",
    title: "Short-run Sensitivity",
    description: "Short-run expenditure coefficients may indicate immediate RSUI responsiveness to spending changes."
  },
  {
    id: "govexp-3",
    type: "success",
    icon: "📊",
    title: "Long-run Structural Impact",
    description: "Long-run expenditure effects help reveal whether government spending has lasting influence on RSUI."
  }
]

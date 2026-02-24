"""
Dashboard router – economic indicators and chart data
"""
from fastapi import APIRouter, Depends
from app.routers.auth import get_current_user
from app.models.schemas import UserOut

router = APIRouter()


# ── Static RSUI data (2000–2016) ──────────────────────────────────────────────
RSUI_TREND = [
    {"year": 2000, "value": 14.2}, {"year": 2001, "value": 15.8},
    {"year": 2002, "value": 18.1}, {"year": 2003, "value": 17.3},
    {"year": 2004, "value": 19.6}, {"year": 2005, "value": 21.2},
    {"year": 2006, "value": 22.8}, {"year": 2007, "value": 28.4},
    {"year": 2008, "value": 24.5}, {"year": 2009, "value": 22.1},
    {"year": 2010, "value": 25.8}, {"year": 2011, "value": 28.2},
    {"year": 2012, "value": 29.6}, {"year": 2013, "value": 31.4},
    {"year": 2014, "value": 33.8}, {"year": 2015, "value": 32.1},
    {"year": 2016, "value": 35.7},
]

CHART_DATA = {
    "pce": [
        {"label": "Food and beverages", "value": 79.78},
        {"label": "Transport",          "value": 23.59},
        {"label": "Housing",            "value": 38.00},
        {"label": "Health",             "value": 20.61},
        {"label": "Education",          "value": 85.04},
        {"label": "Communication",      "value": 67.03},
    ],
    "gdp_sector": [
        {"label": "Agriculture", "value": 98.0},
        {"label": "Services",    "value": 66.0},
        {"label": "Industry",    "value": 88.0},
    ],
    "unemployment_age": [
        {"label": "15–19", "value": 84.79},
        {"label": "20–24", "value": 75.28},
        {"label": "25–29", "value": 28.45},
        {"label": "30–39", "value": 57.03},
        {"label": "40+",   "value": 21.70},
    ],
    "wages_sector": [
        {"label": "workers_in_agriculture",  "value": 65.34},
        {"label": "workers_in_industry",     "value": 19.26},
        {"label": "central_govt_employees",  "value": 89.65},
        {"label": "workers_in_services",     "value": 40.09},
    ],
    "unemployment_education": [
        {"label": "Grade 5 below",    "value": 65.34},
        {"label": "6 to 10",          "value": 19.26},
        {"label": "GCE O/L",          "value": 89.85},
        {"label": "GCE A/L and above","value": 40.09},
    ],
    "agriculture": [
        {"label": "15–19", "value": 84.78},
        {"label": "20–24", "value": 75.28},
        {"label": "25–29", "value": 28.45},
        {"label": "30–39", "value": 57.03},
        {"label": "40+",   "value": 21.70},
    ],
}

STATS = {
    "gdp_change": -6.8,
    "wages_change": 12.3,
    "agriculture_change": 10.5,
    "unemployment_change": 15.1,
    "personal_consumption_change": 15.1,
    "govt_expenditure_change": 6.8,
}

INSIGHTS = [
    {
        "id": "ins-1",
        "type": "danger",
        "icon": "⚠️",
        "title": "High Risk Alert",
        "description": "Employment sector showing critical impact (72.8) with rising unemployment rates. Immediate intervention recommended.",
    },
    {
        "id": "ins-2",
        "type": "warning",
        "icon": "📈",
        "title": "Wage Pressure Increasing",
        "description": "Wages impact index at 68.4 with 12.3% increase. Monitor closely for potential social unrest triggers.",
    },
    {
        "id": "ins-3",
        "type": "success",
        "icon": "🌾",
        "title": "Agriculture Sector Stable",
        "description": "Agricultural impact at moderate level (54.2). Seasonal variations expected in Q2–Q3 period.",
    },
    {
        "id": "ins-4",
        "type": "info",
        "icon": "🛒",
        "title": "Consumption Patterns Shifting",
        "description": "Personal consumption expenditure impact at 61.9. Consumer confidence declining.",
    },
]


@router.get("/stats")
async def get_stats(_: UserOut = Depends(get_current_user)):
    return STATS


@router.get("/charts/{chart_name}")
async def get_chart_data(chart_name: str, _: UserOut = Depends(get_current_user)):
    data = CHART_DATA.get(chart_name)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Chart '{chart_name}' not found")
    return {"chart": chart_name, "data": data}


@router.get("/rsui-trend")
async def get_rsui_trend(range: str = "all", _: UserOut = Depends(get_current_user)):
    if range == "5y":
        return {"range": range, "data": RSUI_TREND[-5:]}
    elif range == "10y":
        return {"range": range, "data": RSUI_TREND[-10:]}
    return {"range": "all", "data": RSUI_TREND}


@router.get("/insights")
async def get_insights(_: UserOut = Depends(get_current_user)):
    return {"insights": INSIGHTS}

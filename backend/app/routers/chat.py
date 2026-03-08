from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pathlib
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.routers.auth import get_current_user
from app.models.schemas import UserOut, ChatMessageIn, ChatMessageOut
from app.services.ai_service import get_ai_response

router = APIRouter()

# In-memory session store keyed by user_id → list of sessions
_sessions: dict[str, list] = {}


# -----------------------------------------------------------------------------
# Dynamic tag vocab from relationship_table.csv (UI only)
# -----------------------------------------------------------------------------
def _find_relationship_table() -> Optional[pathlib.Path]:
    here = pathlib.Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents)[:8]:
        p = parent / "relationship_table.csv"
        if p.exists():
            return p
    p = pathlib.Path.cwd() / "relationship_table.csv"
    if p.exists():
        return p
    return None


_REL_TAG = pd.DataFrame()
try:
    p = _find_relationship_table()
    if p:
        _REL_TAG = pd.read_csv(p)
except Exception:
    _REL_TAG = pd.DataFrame()

INDEP_KEYWORDS = set()
GROUPTYPE_KEYWORDS = set()
GROUPLABEL_KEYWORDS = set()

if not _REL_TAG.empty:
    if "indep_var" in _REL_TAG.columns:
        INDEP_KEYWORDS = set(_REL_TAG["indep_var"].astype(str).str.lower().str.strip())
    if "group_type" in _REL_TAG.columns:
        GROUPTYPE_KEYWORDS = set(_REL_TAG["group_type"].astype(str).str.lower().str.strip())
    if "group_label" in _REL_TAG.columns:
        GROUPLABEL_KEYWORDS = set(_REL_TAG["group_label"].astype(str).str.lower().str.strip())


def _get_user_sessions(user_id: str) -> list:
    return _sessions.setdefault(user_id, [
        {
            "id": "sess-demo-1",
            "title": "Wage Trends vs Unrest",
            "preview": "Compared real wage growth and unrest events (2015–2022)",
            "tag": "Wages",
            "created_at": datetime(2026, 2, 19, 18, 0, tzinfo=timezone.utc).isoformat(),
            "messages": [],
        },
        {
            "id": "sess-demo-2",
            "title": "Unemployment Impact Analysis",
            "preview": "Monthly unemployment data and protest incidents",
            "tag": "Unemployment",
            "created_at": datetime(2026, 2, 19, 17, 30, tzinfo=timezone.utc).isoformat(),
            "messages": [],
        },
        {
            "id": "sess-demo-3",
            "title": "Crisis Years Breakdown",
            "preview": "Focused analysis on 2020–2022",
            "tag": "RSUI",
            "created_at": datetime(2026, 2, 19, 15, 0, tzinfo=timezone.utc).isoformat(),
            "messages": [],
        },
    ])


@router.get("/sessions")
async def list_sessions(current_user: UserOut = Depends(get_current_user)):
    sessions = _get_user_sessions(current_user.id)
    return [{k: v for k, v in s.items() if k != "messages"} for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, current_user: UserOut = Depends(get_current_user)):
    sessions = _get_user_sessions(current_user.id)
    session = next((s for s in sessions if s["id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions", status_code=201)
async def create_session(current_user: UserOut = Depends(get_current_user)):
    sessions = _get_user_sessions(current_user.id)
    new_session = {
        "id": f"sess-{uuid.uuid4().hex[:8]}",
        "title": "New Chat",
        "preview": "",
        "tag": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }
    sessions.insert(0, new_session)
    return new_session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, current_user: UserOut = Depends(get_current_user)):
    sessions = _get_user_sessions(current_user.id)
    _sessions[current_user.id] = [s for s in sessions if s["id"] != session_id]


@router.post("/message", response_model=ChatMessageOut)
async def send_message(
    body: ChatMessageIn,
    current_user: UserOut = Depends(get_current_user),
):
    sessions = _get_user_sessions(current_user.id)

    # Find or create session
    session = next((s for s in sessions if s["id"] == body.session_id), None)
    if not session:
        session = {
            "id": f"sess-{uuid.uuid4().hex[:8]}",
            "title": body.message[:40] + ("…" if len(body.message) > 40 else ""),
            "preview": body.message,
            "tag": _detect_tag(body.message),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        sessions.insert(0, session)

    # Store user message first
    user_msg = {
        "role": "user",
        "content": body.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    session["messages"].append(user_msg)

    # Deterministic (no LLM)
    ai_content = get_ai_response(
        body.message,
        history=session["messages"],
        session_id=session["id"],
    )

    ai_msg = {
        "role": "assistant",
        "content": ai_content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    session["messages"].append(ai_msg)

    # Update session metadata
    session["preview"] = body.message[:80]
    if not session["tag"]:
        session["tag"] = _detect_tag(body.message)
    if session["title"] == "New Chat":
        session["title"] = body.message[:40] + ("…" if len(body.message) > 40 else "")

    return ChatMessageOut(
        session_id=session["id"],
        role="assistant",
        content=ai_content,
    )


def _detect_tag(text: str) -> str:
    """
    Dynamic tag detection (UI-only). Uses relationship_table.csv vocab when available.
    """
    t = (text or "").lower()

    # prioritize RSUI/unrest terms
    if any(w in t for w in ["rsui", "unrest", "protest", "riot", "strike", "demonstration"]):
        return "RSUI"

    # dynamic indep
    for indep in sorted(INDEP_KEYWORDS, key=len, reverse=True):
        if indep and (indep in t or indep.replace("_", " ") in t):
            return indep.replace("_", " ").title()

    # dynamic group_type
    for gt in sorted(GROUPTYPE_KEYWORDS, key=len, reverse=True):
        if gt and (gt in t or gt.replace("_", " ") in t):
            return gt.replace("_", " ").title()

    # dynamic group_label (avoid noisy "Total ..." tags)
    for gl in sorted(GROUPLABEL_KEYWORDS, key=len, reverse=True):
        if gl and (gl in t or gl.replace("_", " ") in t):
            if gl.lower().startswith("total"):
                continue
            return gl.replace("_", " ").title()

    # fallback keywords
    if any(w in t for w in ["government expenditure", "public expenditure", "spending", "budget", "fiscal", "expanditure", "gov exp"]):
        return "Gov Expenditure"
    if any(w in t for w in ["wage", "salary", "earnings", "income", "pay"]):
        return "Wages"
    if any(w in t for w in ["unemployment", "jobless", "employment rate"]):
        return "Unemployment"
    if any(w in t for w in ["gdp", "gross domestic", "sector", "agriculture", "industry", "services"]):
        return "GDP"
    if any(w in t for w in ["pce", "consumption"]):
        return "PCE"

    return ""

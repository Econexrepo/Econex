"""
Chat router – AI response endpoint and session management
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_user
from app.models.schemas import UserOut, ChatMessageIn, ChatMessageOut
from app.services.ai_service import get_ai_response

router = APIRouter()

# In-memory session store keyed by user_id → list of sessions
# Replace with DB persistence in production
_sessions: dict[str, list] = {}


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
    # Return without full messages for the list view
    return [
        {k: v for k, v in s.items() if k != "messages"}
        for s in sessions
    ]


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

    # Generate AI response using CSV-driven keyword engine
    ai_content = get_ai_response(body.message)

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
    t = text.lower()
    if "gdp" in t or "sector" in t:        return "GDP"
    if "wage" in t or "salary" in t:       return "Wages"
    if "unemploy" in t or "job" in t:      return "Unemployment"
    if "agricult" in t or "farm" in t:     return "Agriculture"
    if "consumption" in t or "pce" in t:   return "PCE"
    if "rsui" in t or "unrest" in t:       return "RSUI"
    if "predict" in t or "forecast" in t:  return "Prediction"
    return ""

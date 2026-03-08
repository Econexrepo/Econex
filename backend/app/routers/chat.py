from __future__ import annotations

import uuid
import base64
import json
import binascii
from datetime import datetime, timezone
import pathlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_auth_db
from app.routers.auth import get_current_user
from app.models.schemas import ChartMessageIn, ChartMessageOut, ChatMessageIn, ChatMessageOut, UserOut
from app.services.ai_service import get_ai_response, INDEP_VOCAB, GTYPE_VOCAB, GLABEL_VOCAB

router = APIRouter()
_CHART_UPLOAD_DIR = pathlib.Path(__file__).resolve().parents[2] / "uploads" / "charts"
_CHART_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_CHAT_COLS_AVAILABLE_CACHE: bool | None = None



# Dynamic tag vocab from ai_service (single relationship table load).
INDEP_KEYWORDS = set(INDEP_VOCAB)
GROUPTYPE_KEYWORDS = set(GTYPE_VOCAB)
GROUPLABEL_KEYWORDS = set(GLABEL_VOCAB)

def _iso(ts) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return str(ts)


def _list_user_sessions(db: Session, user_id: str) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT id, title, preview, tag, created_at
            FROM chat_sessions
            WHERE user_id = CAST(:user_id AS UUID)
            ORDER BY updated_at DESC, created_at DESC
        """),
        {"user_id": user_id},
    ).fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "preview": row[2],
            "tag": row[3],
            "created_at": _iso(row[4]),
        }
        for row in rows
    ]
def _get_session_row(db: Session, user_id: str, session_id: str):
    return db.execute(
        text("""
            SELECT id, title, preview, tag, created_at
            FROM chat_sessions
            WHERE id = :session_id AND user_id = CAST(:user_id AS UUID)
            LIMIT 1
        """),
        {"session_id": session_id, "user_id": user_id},
    ).fetchone()


def _get_session_messages(db: Session, session_id: str) -> list[dict]:
    if _chat_columns_available(db):
        rows = db.execute(
            text("""
                SELECT role, content, created_at, message_type, chart_payload, image_path
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at ASC, id ASC
            """),
            {"session_id": session_id},
        ).fetchall()
    else:
        base_rows = db.execute(
            text("""
                SELECT role, content, created_at, message_type
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at ASC, id ASC
            """),
            {"session_id": session_id},
        ).fetchall()
        rows = [(r[0], r[1], r[2], r[3], None, None) for r in base_rows]
    out: list[dict] = []
    for role, content, created_at, message_type, chart_payload, image_path in rows:
        msg = {
            "role": role,
            "content": content,
            "timestamp": _iso(created_at),
            "message_type": message_type or "text",
        }
        if chart_payload is not None:
            msg["chart_payload"] = chart_payload
        if image_path:
            msg["image_url"] = image_path
        out.append(msg)
    return out

def _chat_columns_available(db: Session) -> bool:
    global _CHAT_COLS_AVAILABLE_CACHE
    if _CHAT_COLS_AVAILABLE_CACHE is not None:
        return _CHAT_COLS_AVAILABLE_CACHE
    try:
        rows = db.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'chat_messages'
                  AND table_schema = 'public'
                  AND column_name IN ('chart_payload', 'image_path')
            """)
        ).fetchall()
        found = {r[0] for r in rows}
        _CHAT_COLS_AVAILABLE_CACHE = ("chart_payload" in found and "image_path" in found)
        return _CHAT_COLS_AVAILABLE_CACHE
    except SQLAlchemyError:
        _CHAT_COLS_AVAILABLE_CACHE = False
        return False


def _create_session_record(
    db: Session,
    user_id: str,
    title: str = "New Chat",
    preview: str = "",
    tag: str = "",
) -> dict:
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    row = db.execute(
        text("""
            INSERT INTO chat_sessions (id, user_id, title, preview, tag)
            VALUES (:id, :user_id, :title, :preview, :tag)
            RETURNING id, title, preview, tag, created_at
        """),
        {
            "id": session_id,
            "user_id": user_id,
            "title": title,
            "preview": preview,
            "tag": tag,
        },
    ).fetchone()
    db.commit()
    return {
        "id": row[0],
        "title": row[1],
        "preview": row[2],
        "tag": row[3],
        "created_at": _iso(row[4]),
        "messages": [],
    }


def _save_chart_image(image_data_url: str) -> str:
    if not image_data_url or "," not in image_data_url:
        raise HTTPException(status_code=400, detail="Invalid chart image payload.")
    header, payload = image_data_url.split(",", 1)
    if "base64" not in header:
        raise HTTPException(status_code=400, detail="Chart image must be base64 encoded.")
    ext = "png"
    if "image/jpeg" in header:
        ext = "jpg"
    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid base64 image payload.")
    file_name = f"chart_{uuid.uuid4().hex}.{ext}"
    file_path = _CHART_UPLOAD_DIR / file_name
    file_path.write_bytes(image_bytes)
    return f"/uploads/charts/{file_name}"


def _delete_chart_images_for_session(db: Session, session_id: str) -> None:
    rows = db.execute(
        text("""
            SELECT image_path
            FROM chat_messages
            WHERE session_id = :session_id
              AND image_path IS NOT NULL
              AND image_path <> ''
        """),
        {"session_id": session_id},
    ).fetchall()

    for (image_path,) in rows:
        try:
            # image_path is stored as "/uploads/charts/<file>"
            file_name = pathlib.Path(str(image_path)).name
            if not file_name:
                continue
            local_path = _CHART_UPLOAD_DIR / file_name
            if local_path.exists() and local_path.is_file():
                local_path.unlink()
        except Exception:
            # Do not block session deletion if a file cannot be removed.
            continue


@router.get("/sessions")
async def list_sessions(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    return _list_user_sessions(db, current_user.id)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    row = _get_session_row(db, current_user.id, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": row[0],
        "title": row[1],
        "preview": row[2],
        "tag": row[3],
        "created_at": _iso(row[4]),
        "messages": _get_session_messages(db, session_id),
    }

@router.post("/sessions", status_code=201)
async def create_session(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    return _create_session_record(db, current_user.id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    session = _get_session_row(db, current_user.id, session_id)
    if not session:
        return

    _delete_chart_images_for_session(db, session_id)

    db.execute(
        text("DELETE FROM chat_sessions WHERE id = :session_id AND user_id = CAST(:user_id AS UUID)"),
        {"session_id": session_id, "user_id": current_user.id},
    )
    db.commit()


@router.post("/message", response_model=ChatMessageOut)
async def send_message(
    body: ChatMessageIn,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    session = None
    if body.session_id:
        session = _get_session_row(db, current_user.id, body.session_id)

    if not session:
        title = body.message[:40] + ("..." if len(body.message) > 40 else "")
        session_data = _create_session_record(
            db,
            current_user.id,
            title=title,
            preview=body.message[:80],
            tag=_detect_tag(body.message),
        )
        session_id = session_data["id"]
    else:
        session_id = session[0]

    db.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, message_type)
            VALUES (:session_id, 'user', :content, 'text')
        """),
        {"session_id": session_id, "content": body.message},
    )
    db.commit()

    history = [
        {"role": row[0], "content": row[1]}
        for row in db.execute(
            text("""
                SELECT role, content
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at ASC, id ASC
            """),
            {"session_id": session_id},
        ).fetchall()
    ]

    ai_content = get_ai_response(
        body.message,
        history=history,
        session_id=session_id,
    )

    db.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, message_type)
            VALUES (:session_id, 'assistant', :content, 'text')
        """),
        {"session_id": session_id, "content": ai_content},
    )

    db.execute(
        text("""
            UPDATE chat_sessions
            SET
                preview = :preview,
                tag = CASE WHEN COALESCE(tag, '') = '' THEN :tag ELSE tag END,
                title = CASE
                    WHEN title = 'New Chat' OR COALESCE(title, '') = ''
                    THEN :title
                    ELSE title
                END,
                updated_at = NOW()
            WHERE id = :session_id AND user_id = CAST(:user_id AS UUID)
        """),
        {
            "preview": body.message[:80],
            "tag": _detect_tag(body.message),
            "title": body.message[:40] + ("..." if len(body.message) > 40 else ""),
            "session_id": session_id,
            "user_id": current_user.id,
        },
    )
    db.commit()

    return ChatMessageOut(
        session_id=session_id,
        role="assistant",
        content=ai_content,
    )



@router.post("/chart-message", response_model=ChartMessageOut)
async def send_chart_message(
    body: ChartMessageIn,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    session = None
    if body.session_id:
        session = _get_session_row(db, current_user.id, body.session_id)

    if not session:
        title = body.message[:40] + ("..." if len(body.message) > 40 else "")
        session_data = _create_session_record(
            db,
            current_user.id,
            title=title,
            preview=body.message[:80],
            tag=_detect_tag(body.message),
        )
        session_id = session_data["id"]
    else:
        session_id = session[0]

    db.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, message_type)
            VALUES (:session_id, 'user', :content, 'text')
        """),
        {"session_id": session_id, "content": body.message},
    )

    image_url = _save_chart_image(body.image_data_url) if body.image_data_url else None
    chart_payload_text = json.dumps(body.chart_payload) if body.chart_payload is not None else None
    caption = body.caption or "Chart generated from data warehouse."
    if _chat_columns_available(db):
        db.execute(
            text("""
                INSERT INTO chat_messages (session_id, role, content, message_type, chart_payload, image_path)
                VALUES (
                    :session_id,
                    'assistant',
                    :content,
                    'chart',
                    CASE WHEN :chart_payload IS NULL THEN NULL ELSE CAST(:chart_payload AS JSONB) END,
                    :image_path
                )
            """),
            {
                "session_id": session_id,
                "content": caption,
                "chart_payload": chart_payload_text,
                "image_path": image_url,
            },
        )
    else:
        db.execute(
            text("""
                INSERT INTO chat_messages (session_id, role, content, message_type)
                VALUES (:session_id, 'assistant', :content, 'chart')
            """),
            {"session_id": session_id, "content": caption},
        )

    db.execute(
        text("""
            UPDATE chat_sessions
            SET
                preview = :preview,
                tag = CASE WHEN COALESCE(tag, '') = '' THEN :tag ELSE tag END,
                title = CASE
                    WHEN title = 'New Chat' OR COALESCE(title, '') = ''
                    THEN :title
                    ELSE title
                END,
                updated_at = NOW()
            WHERE id = :session_id AND user_id = CAST(:user_id AS UUID)
        """),
        {
            "preview": body.message[:80],
            "tag": _detect_tag(body.message),
            "title": body.message[:40] + ("..." if len(body.message) > 40 else ""),
            "session_id": session_id,
            "user_id": current_user.id,
        },
    )
    db.commit()

    return ChartMessageOut(
        session_id=session_id,
        role="assistant",
        content=caption,
        message_type="chart",
        image_url=image_url,
    )



def _detect_tag(text: str) -> str:
    """
    Dynamic tag detection (UI-only). Uses relationship_table.csv vocab when available.
    """
    t = (text or "").lower()

    if any(w in t for w in ["rsui", "unrest", "protest", "riot", "strike", "demonstration"]):
        return "RSUI"

    for indep in sorted(INDEP_KEYWORDS, key=len, reverse=True):
        if indep and (indep in t or indep.replace("_", " ") in t):
            return indep.replace("_", " ").title()

    for gt in sorted(GROUPTYPE_KEYWORDS, key=len, reverse=True):
        if gt and (gt in t or gt.replace("_", " ") in t):
            return gt.replace("_", " ").title()

    for gl in sorted(GROUPLABEL_KEYWORDS, key=len, reverse=True):
        if gl and (gl in t or gl.replace("_", " ") in t):
            if gl.lower().startswith("total"):
                continue
            return gl.replace("_", " ").title()

    if any(w in t for w in ["government expenditure", "public expenditure", "spending", "budget", "fiscal", "expanditure", "gov exp"]):
        return "Gov Expenditure"
    if any(w in t for w in ["wage", "salary", "earnings", "income", "pay"]):
        return "Wages"
    if any(w in t for w in ["unemployment", "jobless", "employment rate"]):
        return "Unemployment"
    if any(w in t for w in ["gdp", "gross domestic", "sector", "industry", "services"]):
        return "GDP"
    if any(w in t for w in ["pce", "consumption"]):
        return "PCE"

    return ""

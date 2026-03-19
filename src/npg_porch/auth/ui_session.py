from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from secrets import compare_digest, token_urlsafe
from threading import Lock

from fastapi import HTTPException, Request
from starlette import status
from starlette.responses import Response

from npg_porch.models.permission import Permission

UI_SESSION_COOKIE_NAME = "npg_porch_ui_session"
UI_CSRF_HEADER_NAME = "X-CSRF-Token"
UI_SESSION_TTL_SECONDS = int(os.environ.get("NPG_PORCH_UI_SESSION_TTL", "1800"))
UI_SESSION_COOKIE_SECURE = os.environ.get("NPG_PORCH_MODE") is None


@dataclass
class UiSession:
    session_id: str
    permission: Permission
    csrf_token: str
    expires_at: datetime

    @property
    def pipeline_name(self) -> str | None:
        if self.permission.pipeline:
            return self.permission.pipeline.name
        return None


class UiSessionStore:
    """Stores UI sessions and provides methods for creating, retrieving, and revoking
    sessions."""

    def __init__(self):
        self._sessions: dict[str, UiSession] = {}
        self._lock = Lock()

    def create(self, permission: Permission) -> UiSession:
        """Create a new UI session for the given permission and return it."""

        session = UiSession(
            session_id=token_urlsafe(32),
            permission=permission,
            csrf_token=token_urlsafe(32),
            expires_at=datetime.now() + timedelta(seconds=UI_SESSION_TTL_SECONDS),
        )
        with self._lock:
            self._purge_expired_locked()
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str | None) -> UiSession | None:
        """Return the UI session for the given session ID, or None if not found."""

        if not session_id:
            return None
        with self._lock:
            self._purge_expired_locked()
            return self._sessions.get(session_id)

    def revoke(self, session_id: str | None) -> None:
        """Revoke a UI session by session ID. If the session ID is None, does nothing."""

        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def _purge_expired_locked(self) -> None:
        now = datetime.now()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)


ui_session_store = UiSessionStore()


def set_ui_session_cookie(response: Response, session_id: str) -> None:
    """Set the UI session cookie in the response."""

    # The UI uses an HttpOnly cookie so the browser never has to persist the
    # original bearer token in script-visible storage.
    response.set_cookie(
        key=UI_SESSION_COOKIE_NAME,
        value=session_id,
        max_age=UI_SESSION_TTL_SECONDS,
        path="/",
        secure=UI_SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


def clear_ui_session_cookie(response: Response) -> None:
    """Clear the UI session cookie from the response."""

    response.delete_cookie(UI_SESSION_COOKIE_NAME, path="/")


def get_ui_session(request: Request) -> UiSession | None:
    """Retrieve the UI session from the request cookies."""

    return ui_session_store.get(request.cookies.get(UI_SESSION_COOKIE_NAME))


def build_ui_session_context(request: Request) -> dict:
    """Build the UI session context for the current request."""

    session = get_ui_session(request)
    return {
        "ui_session_active": session is not None,
        "ui_session_pipeline_name": session.pipeline_name if session else None,
        "ui_csrf_token": session.csrf_token if session else None,
    }


def require_ui_session(request: Request) -> UiSession:
    """Require a valid UI session for the current request."""

    session = get_ui_session(request)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UI session required",
        )
    return session


def validate_ui_csrf(request: Request, session: UiSession) -> None:
    """Validate the UI CSRF token for the current request."""

    # Cookie auth fixes token exposure, but browser requests then need CSRF
    # protection to stop cross-site state changes.
    csrf_token = request.headers.get(UI_CSRF_HEADER_NAME)
    if csrf_token is None or not compare_digest(csrf_token, session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

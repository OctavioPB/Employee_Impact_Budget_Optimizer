"""Session manager — authentication state for Streamlit.

Manages the current user session within Streamlit's session_state.
Supports demo-mode login and configurable session timeouts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

from auth.rbac import Role, User, DEMO_USERS_BY_EMAIL, get_demo_user

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SESSION_KEY        = "eibo_session"
_DEFAULT_TIMEOUT_M  = 60   # minutes before session expires
_DEMO_PASSWORD      = "demo"


# ---------------------------------------------------------------------------
# Session dataclass (stored in st.session_state)
# ---------------------------------------------------------------------------

class SessionState:
    """Thin wrapper around st.session_state for auth data."""

    @staticmethod
    def _data() -> dict:
        if _SESSION_KEY not in st.session_state:
            st.session_state[_SESSION_KEY] = {}
        return st.session_state[_SESSION_KEY]

    @classmethod
    def is_authenticated(cls) -> bool:
        d = cls._data()
        if not d.get("authenticated"):
            return False
        # Timeout check
        last_active = d.get("last_active")
        if last_active:
            timeout_m = d.get("timeout_minutes", _DEFAULT_TIMEOUT_M)
            if datetime.utcnow() - last_active > timedelta(minutes=timeout_m):
                cls.logout()
                return False
        return True

    @classmethod
    def current_user(cls) -> Optional[User]:
        if not cls.is_authenticated():
            return None
        return cls._data().get("user")

    @classmethod
    def login(cls, user: User, timeout_minutes: int = _DEFAULT_TIMEOUT_M) -> None:
        d = cls._data()
        d["authenticated"]   = True
        d["user"]            = user
        d["login_time"]      = datetime.utcnow()
        d["last_active"]     = datetime.utcnow()
        d["timeout_minutes"] = timeout_minutes
        logger.info("Session started for %s (role=%s)", user.email, user.role.label)

    @classmethod
    def logout(cls) -> None:
        user = cls._data().get("user")
        st.session_state[_SESSION_KEY] = {}
        if user:
            logger.info("Session ended for %s", user.email)

    @classmethod
    def touch(cls) -> None:
        """Reset the inactivity timer."""
        d = cls._data()
        if d.get("authenticated"):
            d["last_active"] = datetime.utcnow()

    @classmethod
    def session_info(cls) -> dict:
        d = cls._data()
        user = d.get("user")
        login_time = d.get("login_time")
        return {
            "authenticated":  d.get("authenticated", False),
            "user_id":        user.user_id if user else None,
            "email":          user.email if user else None,
            "role":           user.role.label if user else None,
            "login_time":     login_time.isoformat() if login_time else None,
            "session_age_m":  (
                round((datetime.utcnow() - login_time).total_seconds() / 60, 1)
                if login_time else 0
            ),
        }


# ---------------------------------------------------------------------------
# Login UI for Streamlit
# ---------------------------------------------------------------------------

def render_login_gate(demo_mode: bool = True) -> bool:
    """Render login UI if unauthenticated. Returns True if the user is logged in."""
    SessionState.touch()
    if SessionState.is_authenticated():
        return True

    # --- Login page ---
    st.markdown(
        """
        <div style="background-color:#003366; min-height:100vh; display:flex;
                    align-items:center; justify-content:center; padding:40px;">
          <div style="max-width:420px; width:100%;">
            <div style="text-align:center; margin-bottom:40px;">
              <span style="font-family:'Fraunces',Georgia,serif; font-size:32px;
                           font-weight:300; color:#fff;">O</span>
              <em style="font-family:'Fraunces',Georgia,serif; font-size:32px;
                         font-weight:300; font-style:italic; color:#E8C46A;">PB</em>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                          letter-spacing:4px; text-transform:uppercase;
                          color:rgba(255,255,255,0.4); margin-top:8px;">
                EIBO Platform
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown("#### Sign in to EIBO")

        if demo_mode:
            st.info(
                "**Demo mode** — select a role to explore with pre-loaded data.",
                icon="🎭",
            )
            role_label = st.selectbox(
                "Demo role",
                options=[r.label for r in Role],
                index=5,  # Admin
                help="Each role has different permissions and data visibility.",
            )
            selected_role = Role.from_string(role_label)
            demo_user = get_demo_user(selected_role)

            col_a, col_b = st.columns(2)
            with col_a:
                st.caption(f"**User:** {demo_user.full_name}")
            with col_b:
                st.caption(f"**Dept scope:** {', '.join(demo_user.departments) or 'All'}")

            if st.button("Sign in as demo user", type="primary", use_container_width=True):
                SessionState.login(demo_user)
                st.rerun()

        else:
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")

            if st.button("Sign in", type="primary", use_container_width=True):
                user = DEMO_USERS_BY_EMAIL.get(email)
                if user and password == _DEMO_PASSWORD:
                    SessionState.login(user)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    logger.warning("Failed login attempt for email=%r", email)

    return False


def require_auth(demo_mode: bool = True) -> Optional[User]:
    """Ensure the user is authenticated; render login gate if not.

    Returns the current User or None (if the login gate was rendered instead).
    """
    if render_login_gate(demo_mode=demo_mode):
        return SessionState.current_user()
    return None

"""OPB brand system for Streamlit: CSS injection and reusable HTML components."""

import streamlit as st

# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------

_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap');

:root {
  --primary:    #003366;
  --primary-80: #1A4D80;
  --primary-60: #336699;
  --primary-30: #99BBDD;
  --primary-10: #E0EAF4;
  --gold:       #C8982A;
  --gold-light: #E8C46A;
  --dark:       #1C1C2E;
  --mid:        #6B7280;
  --light:      #F4F6F9;
  --white:      #FFFFFF;
  --fd: 'Fraunces', Georgia, serif;
  --fb: 'Plus Jakarta Sans', sans-serif;
}

/* ── App shell ── */
#MainMenu, footer, header { visibility: hidden; }
.stApp { background-color: #F4F6F9; font-family: 'Plus Jakarta Sans', sans-serif; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Sidebar brand ── */
[data-testid="stSidebar"] {
  background-color: #003366 !important;
  border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] .stRadio label {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: rgba(255,255,255,0.45) !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }

/* ── Typography ── */
h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; }
h1 { font-size: 32px !important; font-weight: 400 !important; color: #0a1628 !important; }
h2 { font-size: 22px !important; font-weight: 300 !important; color: #0a1628 !important; }
h3 { font-family: 'Plus Jakarta Sans', sans-serif !important;
     font-size: 16px !important; font-weight: 600 !important; color: #0a1628 !important; }
p  { font-family: 'Plus Jakarta Sans', sans-serif !important;
     font-size: 15px !important; line-height: 1.75 !important; color: #374151 !important; }

/* ── Cards ── */
.eibo-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 4px rgba(0,51,102,0.08);
  margin-bottom: 16px;
}
.eibo-card-top {
  border-top: 3px solid #C8982A;
}
.eibo-card-left {
  border-left: 3px solid #C8982A;
}

/* ── Eyebrow label ── */
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 9px; font-weight: 500;
  letter-spacing: 4px; text-transform: uppercase;
  color: #C8982A; margin-bottom: 10px;
}
.eyebrow::before {
  content: ''; width: 24px; height: 1px;
  background: #C8982A; flex-shrink: 0;
}
.eyebrow-light {
  color: #E8C46A !important;
}
.eyebrow-light::before {
  background: #E8C46A !important;
}

/* ── Section divider ── */
.section-divider {
  height: 1px; background: #E0EAF4;
  margin: 48px 0;
}

/* ── Status badges ── */
.badge { display: inline-flex; align-items: center; gap: 6px;
         border-radius: 20px; padding: 4px 12px;
         font-family: 'Plus Jakarta Sans', sans-serif;
         font-size: 10px; font-weight: 500; }
.badge-green  { background: #E0F7EF; color: #0D5C3A; }
.badge-orange { background: #FEF0E6; color: #7A3800; }
.badge-blue   { background: #E0EAF4; color: #001F4D; }
.badge-purple { background: #F0EBF9; color: #3D1F70; }

/* ── Streamlit button overrides ── */
.stButton > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  border-radius: 6px !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
  background: #ffffff !important;
  border-radius: 12px !important;
  padding: 16px 20px !important;
  box-shadow: 0 1px 4px rgba(0,51,102,0.08) !important;
  border-left: 3px solid #C8982A !important;
}

/* ── Tables ── */
.dataframe thead tr { background-color: #003366 !important; }
.dataframe thead th {
  color: #ffffff !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 10px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  padding: 12px 16px !important;
}
</style>
"""

_NAV_HTML = """
<div style="
  background: rgba(0,51,102,0.97);
  backdrop-filter: blur(12px);
  height: 52px;
  position: sticky; top: 0; z-index: 999;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 0 40px;
  display: flex; align-items: center; justify-content: space-between;
">
  <div style="display:flex; align-items:center; gap:8px;">
    <span style="font-family:'Fraunces',Georgia,serif; font-size:20px; font-weight:300; color:#fff;">O</span>
    <em style="font-family:'Fraunces',Georgia,serif; font-size:20px; font-weight:300; font-style:italic; color:#E8C46A;">PB</em>
  </div>
  <span style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; letter-spacing:3px; text-transform:uppercase; color:rgba(255,255,255,0.4);">
    EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER
  </span>
  <div style="width:52px;"></div>
</div>
"""

_FOOTER_YEAR = __import__("datetime").date.today().strftime("%B %Y").upper()
_FOOTER_HTML = f"""
<div style="
  background-color: #003366;
  padding: 20px 48px;
  display: flex; justify-content: space-between; align-items: center;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 9px; letter-spacing: 3px; text-transform: uppercase;
  color: rgba(255,255,255,0.4);
  margin-top: 64px;
">
  <span>OPB · OCTAVIO PÉREZ BRAVO · EIBO</span>
  <span>{_FOOTER_YEAR}</span>
</div>
"""


def inject_css() -> None:
    """Inject OPB brand CSS. Call once at the top of every page."""
    st.markdown(_BRAND_CSS, unsafe_allow_html=True)


def render_nav() -> None:
    """Render the OPB top navigation bar."""
    st.markdown(_NAV_HTML, unsafe_allow_html=True)


def render_footer() -> None:
    """Render the OPB footer."""
    st.markdown(_FOOTER_HTML, unsafe_allow_html=True)


def hero_section(
    label: str,
    title: str,
    italic_word: str,
    subtitle: str,
    stats: list[tuple[str, str]] | None = None,
) -> None:
    """
    Render a dark hero section with grid texture.

    Args:
        label: Small eyebrow label (rendered as uppercase tag above title)
        title: Main hero title (italic_word will be wrapped in <em>)
        italic_word: The word in `title` to render in Fraunces italic + gold
        subtitle: Sub-headline paragraph
        stats: Optional list of (value, label) tuples for the stat row
    """
    title_html = title.replace(
        italic_word,
        f'<em style="font-style:italic; color:#E8C46A;">{italic_word}</em>',
        1,
    )
    stats_html = ""
    if stats:
        stat_items = "".join(
            f"""
            <div style="border-left:2px solid #C8982A; padding-left:18px;">
              <div style="font-family:'Fraunces',Georgia,serif; font-size:34px;
                          font-weight:300; color:#E8C46A; line-height:1; margin-bottom:8px;">
                {val}
              </div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                          color:rgba(255,255,255,0.5); line-height:1.55;">
                {lbl}
              </div>
            </div>
            """
            for val, lbl in stats
        )
        stats_html = f"""
        <div style="display:flex; gap:48px; margin-top:40px; flex-wrap:wrap;">
          {stat_items}
        </div>
        """

    st.markdown(
        f"""
        <div style="
          background-color: #003366;
          background-image:
            linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size: 48px 48px;
          padding: 0;
        ">
          <div style="max-width:1200px; margin:0 auto; padding:56px 48px;">
            <div style="font-size:9px; font-weight:700; letter-spacing:4px;
                        text-transform:uppercase; color:rgba(255,255,255,0.35);
                        margin-bottom:16px; font-family:'Plus Jakarta Sans',sans-serif;">
              {label}
            </div>
            <h1 style="font-family:'Fraunces',Georgia,serif; font-size:30px;
                       font-weight:300; color:#ffffff; max-width:680px;
                       line-height:1.35; margin:0 0 16px;">
              {title_html}
            </h1>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:14px;
                      color:rgba(255,255,255,0.6); line-height:1.75;
                      max-width:580px; margin:0;">
              {subtitle}
            </p>
            {stats_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def eyebrow(text: str, light: bool = False) -> None:
    """Render a gold eyebrow label."""
    cls = "eyebrow eyebrow-light" if light else "eyebrow"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def section_divider() -> None:
    """Render a section divider line."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def card(content_html: str, variant: str = "top") -> None:
    """Render a styled card. variant: 'top' or 'left'."""
    cls = "eibo-card eibo-card-top" if variant == "top" else "eibo-card eibo-card-left"
    st.markdown(f'<div class="{cls}">{content_html}</div>', unsafe_allow_html=True)


def badge(text: str, color: str = "blue") -> str:
    """Return HTML for a status badge. color: green, orange, blue, purple."""
    return f'<span class="badge badge-{color}">{text}</span>'

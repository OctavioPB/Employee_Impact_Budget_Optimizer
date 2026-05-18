"""OPB design system — implements UI_Decisions.md exactly.

Design philosophy: Corporate authority without excess decoration.
                   Technical precision + executive clarity.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Master CSS (UI_Decisions.md §3 tokens + all component styles)
# ---------------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap');

/* ── Design tokens — UI_Decisions.md §3 ────────────────────────────────── */
:root {
  /* Brand colours */
  --primary:    #003366;
  --primary-80: #1a4d80;
  --primary-60: #336699;
  --primary-30: #99bbdd;
  --primary-10: #e0eaf4;
  --gold:       #c8982a;
  --gold-light: #e8c46a;
  --dark:       #1c1c2e;
  --mid:        #6b7280;
  --light:      #f4f6f9;
  --white:      #ffffff;

  /* Semantic status colours */
  --status-green:        #27b97c;
  --status-red:          #e03448;
  --status-orange:       #f07020;
  --status-purple:       #7c4dbd;
  --status-blue:         #003366;
  --status-green-bg:     rgba(39,185,124,0.08);
  --status-green-text:   #0d5c3a;
  --status-red-bg:       rgba(224,52,72,0.08);
  --status-red-text:     #7a1020;
  --status-orange-bg:    rgba(240,112,32,0.08);
  --status-orange-text:  #7a3800;
  --status-purple-bg:    rgba(124,77,189,0.08);
  --status-purple-text:  #3d1f70;
  --status-blue-bg:      rgba(0,51,102,0.08);
  --status-blue-text:    #001f4d;

  /* Typography */
  --fd: 'Fraunces', Georgia, serif;
  --fb: 'Plus Jakarta Sans', sans-serif;

  /* Spacing — 8-point grid */
  --space-4:  4px;   --space-8:  8px;   --space-12: 12px;
  --space-16: 16px;  --space-24: 24px;  --space-32: 32px;
  --space-40: 40px;  --space-48: 48px;  --space-64: 64px;

  /* Radii */
  --radius-sm:   6px;
  --radius-md:   12px;
  --radius-lg:   14px;
  --radius-pill: 20px;

  /* Shadows */
  --shadow-card: 0 1px 4px rgba(0,51,102,0.08);
  --shadow-soft: 0 1px 6px rgba(0,51,102,0.09);

  /* Layout */
  --max-width-content:   1200px;
  --max-width-dashboard: 1300px;
  --nav-height: 52px;
}

/* ── Dark mode token overrides ─────────────────────────────────────────── */
/* Applied via .stApp[data-theme="dark"] when toggled */
.dark-mode {
  --light:       #0f1117;
  --white:       #1a1d27;
  --dark:        #e2e8f0;
  --mid:         #8b9099;
  --primary-10:  rgba(255,255,255,0.07);
  --shadow-card: 0 1px 4px rgba(0,0,0,0.35);
  --shadow-soft: 0 1px 6px rgba(0,0,0,0.3);
}
.dark-mode .stApp          { background-color: #0f1117 !important; }
.dark-mode .block-container { background-color: #0f1117 !important; }

/* ── App shell reset ───────────────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.stApp                    { background-color: var(--light); font-family: var(--fb); }
.block-container          { padding: 0 !important; max-width: 100% !important; }
.stMainBlockContainer     { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewBlockContainer"] { padding: 0 !important; max-width: 100% !important; }

/* Hide sidebar completely (navigation is top bar) */
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }
.stMainBlockContainer             { margin-left: 0 !important; }

/* ── Top nav bar — :has() sentinel pattern (UI_Decisions.md §7) ─────────
   Streamlit wraps every st.markdown() in its own element-container div,
   so the sentinel and the columns are SIBLINGS at that wrapper level.
   :has() matches the wrapper that CONTAINS the sentinel; + div selects
   the next sibling wrapper (the columns block).                          */

.opb-nav-sentinel { display: none; }

/* Nav bar wrapper — the element-container that holds the columns */
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div,
.block-container      > div:has(.opb-nav-sentinel) + div {
  background-color: var(--primary) !important;
  position:         sticky !important;
  top:              0 !important;
  z-index:          999 !important;
  border-bottom:    1px solid rgba(255,255,255,0.08) !important;
  backdrop-filter:  blur(12px) !important;
  padding:          0 !important;
}

/* Horizontal columns container */
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div [data-testid="stHorizontalBlock"],
.block-container      > div:has(.opb-nav-sentinel) + div [data-testid="stHorizontalBlock"] {
  gap:         0 !important;
  padding:     0 var(--space-24) !important;
  min-height:  var(--nav-height) !important;
  align-items: center !important;
}

/* Each column */
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div [data-testid="column"],
.block-container      > div:has(.opb-nav-sentinel) + div [data-testid="column"] {
  padding:         0 !important;
  display:         flex !important;
  align-items:     center !important;
  justify-content: center !important;
  min-height:      var(--nav-height) !important;
}

/* Inactive nav buttons — navLinkBase (UI_Decisions.md §7) */
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div .stButton > button,
.block-container      > div:has(.opb-nav-sentinel) + div .stButton > button {
  background:       transparent !important;
  background-color: transparent !important;
  border:           none !important;
  box-shadow:       none !important;
  color:            rgba(255,255,255,0.45) !important;
  font-family:      var(--fb) !important;
  font-size:        9px !important;
  font-weight:      500 !important;
  letter-spacing:   2px !important;
  text-transform:   uppercase !important;
  padding:          5px 8px !important;
  border-radius:    var(--radius-sm) !important;
  cursor:           pointer !important;
  transition:       color 0.15s, background-color 0.15s !important;
  white-space:      nowrap !important;
  margin:           0 !important;
  min-height:       unset !important;
  line-height:      1 !important;
}
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div .stButton > button:hover,
.block-container      > div:has(.opb-nav-sentinel) + div .stButton > button:hover {
  color:            rgba(255,255,255,0.8) !important;
  background-color: rgba(255,255,255,0.06) !important;
  border:           none !important;
}
.stMainBlockContainer > div:has(.opb-nav-sentinel) + div .stButton > button:focus,
.block-container      > div:has(.opb-nav-sentinel) + div .stButton > button:focus {
  box-shadow: none !important;
  border:     none !important;
  outline:    none !important;
}

/* Active nav link — navLinkActive (UI_Decisions.md §7) */
.opb-nav-active {
  font-family:    var(--fb);
  font-size:      9px;
  font-weight:    600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color:          var(--gold-light);
  background:     rgba(201,168,76,0.12);
  padding:        5px 8px;
  border-radius:  var(--radius-sm);
  white-space:    nowrap;
  cursor:         default;
  display:        inline-block;
}

/* ── Eyebrow — UI_Decisions.md §9 ─────────────────────────────────────── */
.opb-eyebrow {
  display:        inline-flex;
  align-items:    center;
  gap:            8px;
  font-family:    var(--fb);
  font-size:      9px;
  font-weight:    700;
  letter-spacing: 4px;
  text-transform: uppercase;
  color:          var(--gold);
  margin-bottom:  10px;
}
.opb-eyebrow::before {
  content:     '';
  width:       24px;
  height:      1px;
  background:  var(--gold);
  flex-shrink: 0;
}
.opb-eyebrow-light            { color: var(--gold-light) !important; }
.opb-eyebrow-light::before    { background: var(--gold-light) !important; }

/* ── Section divider ────────────────────────────────────────────────────── */
.opb-divider {
  height:     1px;
  background: var(--primary-10);
  margin:     48px 0;
}

/* ── Status badge / sentiment pill — UI_Decisions.md §9 ───────────────── */
.opb-pill {
  display:         inline-flex;
  align-items:     center;
  gap:             4px;
  border-radius:   var(--radius-pill);
  padding:         2px 8px;
}
.opb-pill-dot {
  width:         5px;
  height:        5px;
  border-radius: 50%;
  flex-shrink:   0;
}
.opb-pill span {
  font-family:    var(--fb);
  font-size:      10px;
  font-weight:    600;
  text-transform: capitalize;
}
.opb-pill-green  { background: var(--status-green-bg);  }
.opb-pill-green  span { color: var(--status-green-text); }
.opb-pill-green  .opb-pill-dot { background: var(--status-green); }
.opb-pill-orange { background: var(--status-orange-bg); }
.opb-pill-orange span { color: var(--status-orange-text); }
.opb-pill-orange .opb-pill-dot { background: var(--status-orange); }
.opb-pill-red    { background: var(--status-red-bg);    }
.opb-pill-red    span { color: var(--status-red-text); }
.opb-pill-red    .opb-pill-dot { background: var(--status-red); }
.opb-pill-purple { background: var(--status-purple-bg); }
.opb-pill-purple span { color: var(--status-purple-text); }
.opb-pill-purple .opb-pill-dot { background: var(--status-purple); }
.opb-pill-blue   { background: var(--status-blue-bg);   }
.opb-pill-blue   span { color: var(--status-blue-text); }
.opb-pill-blue   .opb-pill-dot { background: var(--status-blue); }

/* ── Cards — UI_Decisions.md §9 ────────────────────────────────────────── */
.opb-card {
  background:    var(--white);
  border-radius: var(--radius-md);
  padding:       28px;
  box-shadow:    var(--shadow-card);
  border:        1px solid var(--primary-10);
  margin-bottom: var(--space-16);
}
.opb-card-callout { border-left: 3px solid var(--gold); }
.opb-card-danger  {
  border:     1px solid rgba(176,53,53,0.18);
  background: rgba(176,53,53,0.03);
}

/* ── Tables — UI_Decisions.md §9 ───────────────────────────────────────── */
.dataframe, .opb-table {
  width:          100%;
  border-collapse: collapse;
}
.dataframe thead tr,
.opb-table thead tr { background-color: var(--primary) !important; }
.dataframe thead th,
.opb-table thead th {
  color:          var(--white) !important;
  font-family:    var(--fb) !important;
  font-size:      10px !important;
  font-weight:    600 !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  padding:        12px 16px !important;
  white-space:    nowrap;
}
.dataframe tbody tr:nth-child(odd),
.opb-table  tbody tr:nth-child(odd)  { background: var(--white); }
.dataframe tbody tr:nth-child(even),
.opb-table  tbody tr:nth-child(even) { background: var(--primary-10); }
.dataframe tbody td,
.opb-table  tbody td {
  font-family: var(--fb) !important;
  font-size:   13px !important;
  padding:     10px 16px !important;
  color:       var(--dark) !important;
}

/* ── Streamlit metric cards ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background:    var(--white) !important;
  border-radius: var(--radius-md) !important;
  padding:       20px 24px !important;
  box-shadow:    var(--shadow-card) !important;
  border-left:   3px solid var(--gold) !important;
  border:        1px solid var(--primary-10) !important;
  border-left:   3px solid var(--gold) !important;
}
[data-testid="stMetricLabel"] {
  font-family:    var(--fb) !important;
  font-size:      9px !important;
  font-weight:    600 !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color:          var(--mid) !important;
}
[data-testid="stMetricValue"] {
  font-family: var(--fd) !important;
  font-size:   30px !important;
  font-weight: 300 !important;
  color:       var(--dark) !important;
}
[data-testid="stMetricDelta"] {
  font-family: var(--fb) !important;
  font-size:   11px !important;
}

/* ── Streamlit tabs (Info page Business/Engineering) ───────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background-color: var(--primary) !important;
  padding:          0 48px !important;
  border-bottom:    1px solid rgba(255,255,255,0.1) !important;
  gap:              0 !important;
}
.stTabs [data-baseweb="tab"] {
  background:     none !important;
  border:         none !important;
  border-bottom:  2px solid transparent !important;
  margin-bottom:  -1px !important;
  padding:        14px 24px !important;
  font-family:    var(--fb) !important;
  font-size:      11px !important;
  font-weight:    500 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color:          rgba(255,255,255,0.4) !important;
  transition:     color 0.15s !important;
}
.stTabs [data-baseweb="tab"]:hover   { color: rgba(255,255,255,0.75) !important; background: none !important; }
.stTabs [aria-selected="true"]        { color: var(--gold-light) !important; border-bottom-color: var(--gold-light) !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"]     { padding: 0 !important; }

/* ── Streamlit general buttons (not inside nav) ─────────────────────────── */
.stMainBlockContainer .stButton > button {
  font-family:    var(--fb) !important;
  font-size:      10px !important;
  font-weight:    700 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  border-radius:  var(--radius-sm) !important;
  padding:        8px 18px !important;
  transition:     background 0.15s, color 0.15s !important;
}

/* ── Streamlit sliders / inputs ─────────────────────────────────────────── */
[data-testid="stSlider"] p {
  font-family: var(--fb) !important;
  font-size:   11px !important;
  color:       var(--mid) !important;
}
[data-testid="stSelectbox"] label,
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
  font-family:    var(--fb) !important;
  font-size:      9px !important;
  font-weight:    600 !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color:          var(--mid) !important;
}

/* ── Streamlit expander ─────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  border:        1px solid var(--primary-10) !important;
  border-radius: var(--radius-md) !important;
  background:    var(--white) !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--fb) !important;
  font-size:   13px !important;
  font-weight: 600 !important;
  color:       var(--dark) !important;
  padding:     12px 16px !important;
}

/* ── Typography — global reset ──────────────────────────────────────────── */
h1 { font-family: var(--fd) !important; font-weight: 300 !important; color: var(--dark) !important; line-height: 1.25 !important; }
h2 { font-family: var(--fd) !important; font-size: 22px !important; font-weight: 300 !important; color: var(--dark) !important; line-height: 1.3 !important; }
h3 { font-family: var(--fb) !important; font-size: 16px !important; font-weight: 600 !important; color: var(--dark) !important; }
p  { font-family: var(--fb) !important; font-size: 14px !important; line-height: 1.75 !important; color: #475569 !important; }

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--light); }
::-webkit-scrollbar-thumb { background: var(--primary-30); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* ── Footer ─────────────────────────────────────────────────────────────── */
.opb-footer {
  background-color: var(--primary);
  padding:          20px 48px;
  display:          flex;
  justify-content:  space-between;
  align-items:      center;
  font-family:      var(--fb);
  font-size:        9px;
  letter-spacing:   3px;
  text-transform:   uppercase;
  color:            rgba(255,255,255,0.35);
  margin-top:       64px;
}
</style>
"""

# Dark mode CSS override (injected when theme == "dark")
_DARK_CSS = """
<style>
:root {
  --light:       #0f1117 !important;
  --white:       #1a1d27 !important;
  --dark:        #e2e8f0 !important;
  --mid:         #8b9099 !important;
  --primary-10:  rgba(255,255,255,0.07) !important;
  --shadow-card: 0 1px 4px rgba(0,0,0,0.35) !important;
  --shadow-soft: 0 1px 6px rgba(0,0,0,0.3) !important;
}
.stApp, .block-container,
[data-testid="stAppViewBlockContainer"],
.stMainBlockContainer { background-color: #0f1117 !important; }
p { color: #94a3b8 !important; }
</style>
"""

# Month string for footer
_MONTH = __import__("datetime").date.today().strftime("%B %Y").upper()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_css() -> None:
    """Inject OPB design system CSS. Call once at the very top of main()."""
    st.markdown(_CSS, unsafe_allow_html=True)
    if st.session_state.get("theme") == "dark":
        st.markdown(_DARK_CSS, unsafe_allow_html=True)


def render_footer() -> None:
    """Dark navy footer — OPB signature + current month."""
    st.markdown(
        f'<div class="opb-footer">'
        f'  <span>OPB · OCTAVIO PÉREZ BRAVO · EIBO</span>'
        f'  <span>{_MONTH}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def hero_section(
    label: str,
    title: str,
    italic_word: str,
    subtitle: str,
    stats: list[tuple[str, str]] | None = None,
    tab_bar: bool = False,
) -> None:
    """Dark navy hero section with grid texture.

    UI_Decisions.md §8: padding-bottom:0 when tab_bar=True so the tab bar
    merges with the hero border. Use 56px bottom padding otherwise.
    """
    title_html = title.replace(
        italic_word,
        f'<em style="font-style:italic;color:var(--gold-light);">{italic_word}</em>',
        1,
    )
    stats_html = ""
    if stats:
        items = "".join(
            f"""
            <div style="border-left:2px solid var(--gold);padding-left:18px;">
              <div style="font-family:var(--fd);font-size:34px;font-weight:300;
                          color:var(--gold-light);line-height:1;margin-bottom:8px;">
                {v}
              </div>
              <div style="font-family:var(--fb);font-size:12px;
                          color:rgba(255,255,255,0.5);line-height:1.55;">
                {lb}
              </div>
            </div>
            """
            for v, lb in stats
        )
        stats_html = (
            '<div style="display:flex;gap:48px;margin-top:40px;flex-wrap:wrap;">'
            + items
            + "</div>"
        )

    padding_bottom = "0" if tab_bar else "56px"
    st.markdown(
        f"""
        <div style="
          background-color: var(--primary);
          background-image:
            linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size: 48px 48px;
          padding: 48px 48px {padding_bottom};
        ">
          <div style="max-width:var(--max-width-dashboard);margin:0 auto;">
            <div class="opb-eyebrow opb-eyebrow-light">{label}</div>
            <h1 style="font-family:var(--fd);font-size:36px;font-weight:300;
                       color:var(--white);max-width:680px;line-height:1.3;
                       margin:0 0 16px;">
              {title_html}
            </h1>
            <p style="font-family:var(--fb);font-size:14px;
                      color:rgba(255,255,255,0.6);line-height:1.75;
                      max-width:580px;margin:0;">
              {subtitle}
            </p>
            {stats_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def eyebrow(text: str, light: bool = False) -> None:
    """Gold eyebrow label — dark or light variant. UI_Decisions.md §9."""
    cls = "opb-eyebrow opb-eyebrow-light" if light else "opb-eyebrow"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def section_title(text: str, italic: str = "") -> None:
    """Fraunces 22px / weight 300 section title with optional italic emphasis."""
    if italic:
        display = text.replace(
            italic,
            f'<em style="font-style:italic;color:var(--gold);">{italic}</em>',
            1,
        )
    else:
        display = text
    st.markdown(
        f'<h2 style="font-family:var(--fd);font-size:22px;font-weight:300;'
        f'color:var(--dark);margin:4px 0 8px;">{display}</h2>',
        unsafe_allow_html=True,
    )


def section_divider() -> None:
    """1px solid primary-10 divider. Use between major page sections."""
    st.markdown('<div class="opb-divider"></div>', unsafe_allow_html=True)


def card(content_html: str, callout: bool = False, danger: bool = False) -> None:
    """White card. callout=True adds gold left border; danger=True adds red tint."""
    cls = "opb-card"
    if callout:
        cls += " opb-card-callout"
    if danger:
        cls += " opb-card-danger"
    st.markdown(f'<div class="{cls}">{content_html}</div>', unsafe_allow_html=True)


def pill(text: str, color: str = "blue") -> str:
    """Return HTML for a semantic status pill. color: green|orange|red|purple|blue."""
    return (
        f'<div class="opb-pill opb-pill-{color}" style="display:inline-flex;">'
        f'  <div class="opb-pill-dot"></div>'
        f'  <span>{text}</span>'
        f'</div>'
    )


def kpi_hero(value: str, label: str) -> str:
    """Return HTML for a hero-section KPI stat (dark background variant)."""
    return (
        f'<div style="border-left:2px solid var(--gold);padding-left:18px;">'
        f'  <div style="font-family:var(--fd);font-size:34px;font-weight:300;'
        f'              color:var(--gold-light);line-height:1;margin-bottom:8px;">{value}</div>'
        f'  <div style="font-family:var(--fb);font-size:12px;color:rgba(255,255,255,0.5);">{label}</div>'
        f'</div>'
    )


def decorative_numeral(num: str | int) -> str:
    """Return HTML for a ghosted decorative sequence numeral. UI_Decisions.md §9."""
    return (
        f'<div style="font-family:var(--fd);font-size:44px;font-weight:300;'
        f'color:var(--primary-30);line-height:1;margin-bottom:2px;user-select:none;">{num}</div>'
        f'<div style="width:36px;height:3px;background:var(--gold);border-radius:2px;margin:6px 0 12px;"></div>'
    )

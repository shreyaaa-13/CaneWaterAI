"""Agricultural Design System & Custom CSS for CaneWater AI."""

FOREST_GREEN = "#1B4332"
SUGARCANE_ACCENT = "#2D6A4F"
EMERALD_GREEN = "#40916C"
LIGHT_GREEN = "#52B788"
MINT_GREEN = "#D8F3DC"
WARM_BG = "#F8F9FA"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E2E8F0"
TEXT_DARK = "#1A2E22"
TEXT_MUTED = "#4B5563"

CSS = f"""
<style>
/* Import Clean Inter Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: {TEXT_DARK};
}}

.block-container {{
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}}

/* Top App Header */
.cw-header {{
    background: linear-gradient(135deg, {FOREST_GREEN} 0%, {SUGARCANE_ACCENT} 100%);
    color: white;
    padding: 1.1rem 1.6rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(27, 67, 50, 0.12);
}}

.cw-header h1 {{
    color: #FFFFFF !important;
    font-size: 1.65rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}

.cw-header p {{
    color: #E2E8F0;
    font-size: 0.88rem;
    margin: 0.25rem 0 0 0;
}}

.cw-header-badges {{
    display: flex;
    gap: 0.6rem;
    align-items: center;
}}

/* Pills & Status Badges */
.cw-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}}

.cw-pill-green {{
    background: #E8F5E9;
    color: #1B5E20;
    border: 1px solid #A5D6A7;
}}

.cw-pill-amber {{
    background: #FFF8E1;
    color: #8D6E00;
    border: 1px solid #FFE082;
}}

.cw-pill-blue {{
    background: #E3F2FD;
    color: #0D47A1;
    border: 1px solid #90CAF9;
}}

.cw-pill-red {{
    background: #FFEBEE;
    color: #B71C1C;
    border: 1px solid #FFCDD2;
}}

.cw-pill-slate {{
    background: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}}

/* Cards & Surfaces */
.cw-card {{
    background: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    margin-bottom: 1.1rem;
}}

.cw-card-highlight {{
    background: #FCFDFB;
    border: 1px solid #C7E5D0;
    border-left: 4px solid {EMERALD_GREEN};
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
}}

.cw-metric-card {{
    background: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 1rem 1.1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    border-top: 3px solid {EMERALD_GREEN};
    height: 100%;
}}

.cw-metric-title {{
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {TEXT_MUTED};
    margin-bottom: 0.35rem;
}}

.cw-metric-value {{
    font-size: 1.55rem;
    font-weight: 700;
    color: {TEXT_DARK};
    margin: 0;
    line-height: 1.2;
}}

.cw-metric-sub {{
    font-size: 0.76rem;
    color: #6B7280;
    margin-top: 0.3rem;
}}

/* Workflow Stepper */
.cw-stepper {{
    display: flex;
    justify-content: space-between;
    background: #F3F7F4;
    border: 1px solid #D1E7D8;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 1.2rem;
}}

.cw-step-item {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: #4A5568;
}}

.cw-step-item.active {{
    color: {FOREST_GREEN};
    font-weight: 700;
}}

.cw-step-num {{
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #CBD5E1;
    color: #1E293B;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
}}

.cw-step-item.active .cw-step-num {{
    background: {EMERALD_GREEN};
    color: white;
}}

/* Educational Disclaimer Banner */
.cw-disclaimer {{
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 4px solid #D97706;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: #92400E;
    font-size: 0.82rem;
    line-height: 1.45;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
}}

/* Tag Labels for Origin */
.cw-tag {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}}

.cw-tag-calc {{
    background: #E8F5E9;
    color: #1B5E20;
    border: 1px solid #C8E6C9;
}}

.cw-tag-ai {{
    background: #FFF3E0;
    color: #E65100;
    border: 1px solid #FFE0B2;
}}

.cw-tag-user {{
    background: #E3F2FD;
    color: #0D47A1;
    border: 1px solid #BBDEFB;
}}

/* Hero Section */
.cw-hero {{
    background: linear-gradient(135deg, #133926 0%, #1B4332 50%, #2D6A4F 100%);
    color: white;
    border-radius: 16px;
    padding: 2.2rem 2.4rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(27, 67, 50, 0.18);
}}

.cw-hero::after {{
    content: "🌾";
    position: absolute;
    right: 2rem;
    bottom: -1rem;
    font-size: 8rem;
    opacity: 0.12;
    pointer-events: none;
}}

.cw-hero-badge {{
    display: inline-block;
    background: rgba(255, 255, 255, 0.18);
    backdrop-filter: blur(8px);
    color: #A7F3D0;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 0.8rem;
    letter-spacing: 0.03em;
    border: 1px solid rgba(255, 255, 255, 0.2);
}}

.cw-hero h2 {{
    color: #FFFFFF !important;
    font-size: 2.1rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}}

.cw-hero p.subtitle {{
    color: #D1FAE5;
    font-size: 1.05rem;
    max-width: 820px;
    line-height: 1.55;
    margin: 0 0 1.2rem 0;
    font-weight: 400;
}}

/* Clean Plotly Container */
.cw-chart-box {{
    background: #FFFFFF;
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.02);
}}

/* Pipeline Flow visual in Validation Lab */
.cw-pipeline {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin: 1.2rem 0;
    flex-wrap: wrap;
    gap: 0.6rem;
}}

.cw-pipe-node {{
    background: white;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    text-align: center;
    font-size: 0.82rem;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    min-width: 120px;
}}

.cw-pipe-node.active {{
    border-color: {EMERALD_GREEN};
    background: #F0FDF4;
    color: {FOREST_GREEN};
}}

.cw-pipe-arrow {{
    color: #94A3B8;
    font-weight: 700;
    font-size: 1.1rem;
}}

/* Form section headers */
.cw-form-section {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {FOREST_GREEN};
    margin: 1rem 0 0.4rem 0;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #E8F5E9;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
</style>
"""


def apply_custom_styles():
    """Inject custom agricultural technology CSS."""
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def render_tag(kind: str):
    """Render an origin tag: user input, calculation, or GenAI."""
    import streamlit as st
    mapping = {
        "user": ('cw-tag-user', 'User-Entered Input'),
        "calc": ('cw-tag-calc', 'Deterministic Calculation'),
        "ai": ('cw-tag-ai', 'AI-Generated Explanation (GPT-OSS-20B)'),
    }
    css_class, label = mapping.get(kind, ('cw-tag-calc', 'Deterministic Calculation'))
    st.markdown(f'<span class="cw-tag {css_class}">{label}</span>', unsafe_allow_html=True)


def render_disclaimer():
    """Render the educational-prototype disclaimer."""
    import streamlit as st
    st.markdown(
        """
        <div class="cw-disclaimer">
            <span style="font-size: 1.15rem; line-height: 1;">⚠️</span>
            <div>
                <strong>Educational Prototype Disclaimer:</strong>
                This system provides illustrative estimates based on transparent mathematical formulas and manually
                entered inputs. It is <em>not</em> an agronomically certified recommendation. Verify irrigation decisions
                with actual field measurements, local agricultural extension officers, and qualified advisers.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

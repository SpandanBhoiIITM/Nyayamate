"""CSS theme for NyayaMate AI."""

IVORY = "#F7F5EF"
GREEN = "#164B3C"
CHARCOAL = "#202824"
GOLD = "#C6A15B"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, button {{
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}
.stApp {{ background: {IVORY}; color: {CHARCOAL}; }}
.block-container {{ padding-top: 2rem; max-width: 1180px; }}
h1, h2, h3 {{ color: {CHARCOAL}; letter-spacing: -0.01em; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ background: {GREEN}; }}
section[data-testid="stSidebar"] * {{ color: #EDEBE3 !important; }}
section[data-testid="stSidebar"] .stRadio label {{
  padding: .45rem .7rem; border-radius: 10px; margin-bottom: 2px; width: 100%;
  transition: background .15s;
}}
section[data-testid="stSidebar"] .stRadio label:hover {{ background: rgba(255,255,255,.08); }}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {{
  background: rgba(198,161,91,.22); border-left: 3px solid {GOLD};
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.15); }}
.nm-brand {{ font-family: 'Fraunces', Georgia, serif; font-size: 1.55rem; font-weight: 600;
  color: #fff !important; }}
.nm-brand span {{ color: {GOLD} !important; }}
.nm-tag {{ font-size: .78rem; opacity: .75; margin-top: -4px; }}

/* Hero */
.nm-hero {{ background: linear-gradient(135deg, {GREEN} 0%, #0F3A2E 100%); color: #fff;
  border-radius: 20px; padding: 2.1rem 2.3rem; position: relative; overflow: hidden;
  box-shadow: 0 10px 30px rgba(22,75,60,.18); }}
.nm-hero:after {{ content: ""; position: absolute; right: -60px; top: -60px; width: 240px;
  height: 240px; border-radius: 50%; border: 2px solid rgba(198,161,91,.35); }}
.nm-hero h1 {{ color: #fff; font-family: 'Fraunces', Georgia, serif; font-size: 2.1rem;
  margin: 0 0 .4rem 0; }}
.nm-hero p {{ color: #DCE6E1; font-size: 1.02rem; max-width: 720px; margin: 0; }}
.nm-hero .nm-kicker {{ color: {GOLD}; text-transform: uppercase; letter-spacing: .14em;
  font-size: .75rem; font-weight: 600; margin-bottom: .6rem; }}

/* Cards */
.nm-card {{ background: #fff; border: 1px solid #E7E2D6; border-radius: 16px;
  padding: 1.15rem 1.25rem; box-shadow: 0 2px 10px rgba(32,40,36,.05); height: 100%;
  margin-bottom: .8rem; }}
.nm-card h4 {{ margin: 0 0 .35rem 0; color: {GREEN}; font-size: 1.02rem; }}
.nm-card p {{ margin: 0; font-size: .9rem; color: #4A524E; }}
.nm-icon {{ font-size: 1.5rem; display: inline-flex; width: 44px; height: 44px;
  align-items: center; justify-content: center; border-radius: 12px;
  background: #F1ECDF; margin-bottom: .6rem; }}
.nm-stat {{ font-size: 1.7rem; font-weight: 700; color: {GREEN}; }}
.nm-stat-label {{ font-size: .8rem; color: #6B726E; text-transform: uppercase;
  letter-spacing: .06em; }}

/* Badges */
.nm-badge {{ display: inline-block; padding: .18rem .6rem; border-radius: 999px;
  font-size: .74rem; font-weight: 600; margin-right: .3rem; }}
.nm-badge.ai {{ background: #E3EFEA; color: {GREEN}; }}
.nm-badge.demo {{ background: #FBEFD5; color: #8A6216; }}
.nm-badge.warn {{ background: #FCE8E3; color: #9B3A22; }}
.nm-badge.ok {{ background: #E3EFEA; color: {GREEN}; }}
.nm-badge.gold {{ background: #F4EAD5; color: #7A5C1E; }}
.nm-badge.grey {{ background: #ECEAE4; color: #4A524E; }}

/* Disclaimer */
.nm-disclaimer {{ background: #FFF9EC; border: 1px solid #EBD9AE; border-left: 4px solid {GOLD};
  border-radius: 12px; padding: .75rem 1rem; font-size: .85rem; color: #5B4A22;
  margin: .5rem 0 1rem 0; }}
.nm-demo-banner {{ background: #FBEFD5; border: 1px dashed #C6A15B; border-radius: 12px;
  padding: .6rem 1rem; color: #7A5C1E; font-weight: 600; font-size: .88rem;
  margin-bottom: .8rem; }}

/* Steps */
.nm-step {{ display: flex; gap: .8rem; padding: .7rem 0; border-bottom: 1px dashed #E3DDCF; }}
.nm-step-num {{ flex: 0 0 30px; height: 30px; border-radius: 50%; background: {GREEN};
  color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 600;
  font-size: .85rem; }}
.nm-step-body b {{ color: {CHARCOAL}; }}
.nm-step-body div {{ color: #4A524E; font-size: .92rem; }}

/* Document preview */
.nm-doc {{ background: #fff; border: 1px solid #E2DCCD; border-radius: 6px;
  padding: 2rem 2.2rem; font-family: Georgia, 'Times New Roman', serif; line-height: 1.6;
  white-space: pre-wrap; box-shadow: 0 6px 24px rgba(32,40,36,.08); color: #1d1d1d; }}
.nm-draft-stamp {{ display: inline-block; border: 2px solid #B4472A; color: #B4472A;
  padding: .15rem .6rem; border-radius: 6px; font-weight: 700; letter-spacing: .1em;
  font-size: .78rem; transform: rotate(-2deg); margin-bottom: .8rem; }}

/* Buttons */
.stButton > button, .stDownloadButton > button {{ border-radius: 10px; font-weight: 600;
  border: 1px solid {GREEN}; color: {GREEN}; background: #fff; }}
.stButton > button[kind="primary"] {{ background: {GREEN}; color: #fff; border: none; }}
.stButton > button[kind="primary"]:hover {{ background: #0F3A2E; color: #fff; }}
.stButton > button:hover {{ border-color: {GOLD}; color: {CHARCOAL}; }}

/* Chat */
[data-testid="stChatMessage"] {{ background: #fff; border: 1px solid #ECE7DA;
  border-radius: 14px; }}
.stProgress > div > div > div > div {{ background-color: {GOLD}; }}
</style>
"""

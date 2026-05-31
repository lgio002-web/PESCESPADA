"""
Pesce Spada Beach Club — Sistema Prenotazioni Tavoli
Streamlit Web App con Google Sheets (gspread diretto).
Ogni operazione di scrittura legge SEMPRE fresco dal foglio (no cache).
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date
import uuid

# ─────────────────────────────────────────────────────────────
# CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pesce Spada Beach Club",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────
ZONES = {
    "Spiaggia": {
        "color": "#3D7EA6",
        "icon": "🏖️",
        "tables": ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    },
    "Privé": {
        "color": "#7B5EA7",
        "icon": "✨",
        "tables": ["privè1", "privè2", "Privè3", "Privè4"]
    },
    "Sala": {
        "color": "#C5975B",
        "icon": "🍽️",
        "tables": ["1", "2", "3", "4", "5", "7", "8", "10", "11", "14"]
    },
    "Veranda": {
        "color": "#5B8C5A",
        "icon": "🌿",
        "tables": ["V1", "V2", "15", "A1", "A2", "A3"]
    },
    "Patio": {
        "color": "#D4883E",
        "icon": "☀️",
        "tables": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
    },
    "Tiki Bar": {
        "color": "#A63D3D",
        "icon": "🍹",
        "tables": ["D1", "D2", "D3", "D4", "O1", "O2"]
    },
}

ALL_TABLES = []
for zone_data in ZONES.values():
    ALL_TABLES.extend(zone_data["tables"])

TIME_SLOTS = ["Pranzo", "Aperitivo", "Night"]
BOOKING_SOURCES = ["IG", "TikTok", "Facebook", "Twitter", "Telefono", "SMS", "Altro"]

USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "mattia": {"password": "mattia2026", "role": "user"},
    "staff1": {"password": "staff2026", "role": "user"},
    "staff2": {"password": "staff2026", "role": "user"},
}

SHEET_COLUMNS = [
    "ID", "Tavolo", "Cliente", "Data", "Fascia_Oraria",
    "Fonte_Prenotazione", "Creato_Da", "Data_Creazione", "Ultima_Modifica"
]

# ─────────────────────────────────────────────────────────────
# LOGO SVG — Pesce Spada Beach Club (pesce spada oro su fondo crema)
# ─────────────────────────────────────────────────────────────
LOGO_SVG = """
<svg viewBox="0 0 260 80" xmlns="http://www.w3.org/2000/svg" width="220" height="68">
  <rect width="260" height="80" rx="10" fill="#F5EFE4"/>
  <!-- Pesce spada stilizzato -->
  <g transform="translate(8, 12)">
    <!-- Corpo pesce -->
    <path d="M35 28 C28 22 20 22 15 26 L6 28 C4 28 2 30 4 32
             C6 34 15 36 20 35 C25 38 30 36 35 32 Z"
          fill="#B8864A" opacity="0.9"/>
    <!-- Spada/rostro -->
    <line x1="6" y1="28" x2="0" y2="26" stroke="#B8864A" stroke-width="1.8" stroke-linecap="round"/>
    <!-- Pinna dorsale -->
    <path d="M22 22 L26 14 L30 22" fill="#B8864A" opacity="0.7"/>
    <!-- Pinna caudale -->
    <path d="M35 28 L42 22 L42 36 Z" fill="#B8864A" opacity="0.7"/>
    <!-- Occhio -->
    <circle cx="14" cy="29" r="1.5" fill="#3D3D3D"/>
    <!-- Pinna ventrale -->
    <path d="M22 36 L26 44 L30 36" fill="#B8864A" opacity="0.5"/>
  </g>
  <!-- Testo -->
  <text x="58" y="30" font-family="Georgia, serif" font-size="18" font-weight="bold"
        fill="#B8864A" letter-spacing="1">PESCE</text>
  <text x="58" y="52" font-family="Georgia, serif" font-size="18" font-weight="bold"
        fill="#B8864A" letter-spacing="1">SPADA</text>
  <text x="58" y="68" font-family="Georgia, serif" font-size="9"
        fill="#8B7D6B" letter-spacing="3">BEACH CLUB</text>
</svg>
"""

# Logo piccolo per header
LOGO_SMALL_SVG = """
<svg viewBox="0 0 200 50" xmlns="http://www.w3.org/2000/svg" width="180" height="45">
  <rect width="200" height="50" rx="8" fill="#F5EFE4"/>
  <g transform="translate(6, 8)">
    <path d="M25 18 C20 14 14 14 10 17 L4 18 C2 18 1 20 3 21
             C5 22 10 23 14 22 C18 24 22 23 25 20 Z"
          fill="#B8864A" opacity="0.9"/>
    <line x1="4" y1="18" x2="0" y2="17" stroke="#B8864A" stroke-width="1.2" stroke-linecap="round"/>
    <path d="M15 14 L18 9 L21 14" fill="#B8864A" opacity="0.7"/>
    <path d="M25 18 L30 14 L30 23 Z" fill="#B8864A" opacity="0.7"/>
    <circle cx="10" cy="19" r="1" fill="#3D3D3D"/>
  </g>
  <text x="42" y="22" font-family="Georgia, serif" font-size="13" font-weight="bold"
        fill="#B8864A" letter-spacing="1">PESCE SPADA</text>
  <text x="42" y="38" font-family="Georgia, serif" font-size="7"
        fill="#8B7D6B" letter-spacing="2.5">BEACH CLUB</text>
</svg>
"""

# ─────────────────────────────────────────────────────────────
# MAPPA SVG della sala — Layout Summer 2026 (dal PDF)
# Solo per consultazione rapida, senza legenda
# ─────────────────────────────────────────────────────────────
FLOOR_PLAN_SVG = """
<svg viewBox="0 0 640 760" xmlns="http://www.w3.org/2000/svg"
     style="width:100%; height:auto; background:#111; border-radius:10px; padding:6px;">

  <!-- Titolo -->
  <text x="320" y="22" text-anchor="middle" font-family="Inter,sans-serif" font-size="10"
        fill="#C5A55A" font-weight="bold" letter-spacing="2">LAYOUT SUMMER 2026</text>

  <!-- ═══ SPIAGGIA (blu) ═══ -->
  <rect x="65" y="40" width="75" height="42" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="102" y="66" text-anchor="middle" font-size="11" fill="#3D7EA6" font-weight="600">S6</text>
  <rect x="210" y="40" width="85" height="48" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="252" y="70" text-anchor="middle" font-size="11" fill="#3D7EA6" font-weight="600">S7</text>

  <rect x="65" y="98" width="80" height="42" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="105" y="124" text-anchor="middle" font-size="11" fill="#3D7EA6" font-weight="600">S5</text>
  <rect x="210" y="98" width="85" height="48" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="252" y="128" text-anchor="middle" font-size="11" fill="#3D7EA6" font-weight="600">S8</text>

  <!-- Spiaggia laterale sinistra -->
  <rect x="8" y="215" width="48" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="32" y="234" text-anchor="middle" font-size="10" fill="#3D7EA6">S4</text>
  <rect x="38" y="280" width="52" height="28" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="64" y="298" text-anchor="middle" font-size="10" fill="#3D7EA6">S3</text>
  <rect x="8" y="355" width="48" height="28" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="32" y="373" text-anchor="middle" font-size="10" fill="#3D7EA6">S0</text>
  <rect x="38" y="420" width="52" height="28" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="64" y="438" text-anchor="middle" font-size="10" fill="#3D7EA6">S2</text>
  <rect x="8" y="510" width="48" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.4"/>
  <text x="32" y="529" text-anchor="middle" font-size="10" fill="#3D7EA6">S1</text>

  <!-- BEACH arrow -->
  <polygon points="15,190 60,183 60,197" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="66" y="193" font-size="8" fill="#5B8C5A" font-weight="bold">BEACH</text>

  <!-- ═══ PRIVÉ (azzurro) ═══ -->
  <rect x="420" y="40" width="72" height="34" rx="3" fill="none" stroke="#00BCD4" stroke-width="1.4"/>
  <text x="456" y="62" text-anchor="middle" font-size="9" fill="#00BCD4">privè2</text>
  <rect x="530" y="40" width="72" height="34" rx="3" fill="none" stroke="#00BCD4" stroke-width="1.4"/>
  <text x="566" y="62" text-anchor="middle" font-size="9" fill="#00BCD4">Privè3</text>
  <rect x="420" y="90" width="72" height="34" rx="3" fill="none" stroke="#00BCD4" stroke-width="1.4"/>
  <text x="456" y="112" text-anchor="middle" font-size="9" fill="#00BCD4">privè1</text>
  <rect x="530" y="90" width="72" height="34" rx="3" fill="none" stroke="#00BCD4" stroke-width="1.4"/>
  <text x="566" y="112" text-anchor="middle" font-size="9" fill="#00BCD4">Privè4</text>

  <!-- ═══ SALA (arancione — rettangolo grande) ═══ -->
  <rect x="115" y="195" width="285" height="380" rx="4" fill="none" stroke="#D4883E" stroke-width="2"/>
  <text x="200" y="188" font-size="12" fill="#D4883E" font-weight="bold" letter-spacing="3">SALA</text>

  <!-- Tavoli dentro SALA -->
  <rect x="140" y="220" width="52" height="40" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="166" y="245" text-anchor="middle" font-size="11" fill="#D4883E">4</text>
  <rect x="220" y="220" width="48" height="38" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="244" y="244" text-anchor="middle" font-size="11" fill="#D4883E">5</text>
  <rect x="310" y="220" width="60" height="42" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="340" y="246" text-anchor="middle" font-size="11" fill="#D4883E">14</text>

  <rect x="140" y="280" width="52" height="35" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="166" y="302" text-anchor="middle" font-size="11" fill="#D4883E">3</text>
  <rect x="220" y="285" width="55" height="38" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="248" y="309" text-anchor="middle" font-size="11" fill="#D4883E">7</text>

  <rect x="140" y="340" width="52" height="35" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="166" y="362" text-anchor="middle" font-size="11" fill="#D4883E">2</text>
  <rect x="220" y="342" width="55" height="38" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="248" y="366" text-anchor="middle" font-size="11" fill="#D4883E">8</text>

  <rect x="140" y="410" width="52" height="38" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="166" y="434" text-anchor="middle" font-size="11" fill="#D4883E">1</text>
  <rect x="210" y="425" width="55" height="32" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="238" y="446" text-anchor="middle" font-size="10" fill="#D4883E">10</text>
  <rect x="310" y="410" width="60" height="42" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="340" y="436" text-anchor="middle" font-size="11" fill="#D4883E">11</text>

  <!-- ═══ VERANDA ═══ -->
  <text x="480" y="255" font-size="11" fill="#5B8C5A" font-weight="bold" letter-spacing="1">VERANDA</text>
  <rect x="435" y="210" width="60" height="32" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="465" y="230" text-anchor="middle" font-size="10" fill="#5B8C5A">V2</text>
  <rect x="435" y="295" width="65" height="38" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="468" y="319" text-anchor="middle" font-size="10" fill="#5B8C5A">15</text>
  <rect x="410" y="385" width="65" height="32" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="442" y="405" text-anchor="middle" font-size="10" fill="#5B8C5A">V1</text>
  <!-- A1, A2, A3 -->
  <circle cx="525" cy="400" r="17" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="525" y="404" text-anchor="middle" font-size="9" fill="#5B8C5A">A2</text>
  <circle cx="580" cy="400" r="17" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="580" y="404" text-anchor="middle" font-size="9" fill="#5B8C5A">A1</text>
  <circle cx="85" cy="365" r="16" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="85" y="369" text-anchor="middle" font-size="9" fill="#5B8C5A">A3</text>

  <!-- O1, O2 (cerchi rossi) -->
  <circle cx="22" cy="465" r="13" fill="none" stroke="#A63D3D" stroke-width="1.3"/>
  <text x="22" y="469" text-anchor="middle" font-size="8" fill="#A63D3D">O1</text>
  <circle cx="22" cy="270" r="13" fill="none" stroke="#A63D3D" stroke-width="1.3"/>
  <text x="22" y="274" text-anchor="middle" font-size="8" fill="#A63D3D">O2</text>

  <!-- EXIT -->
  <text x="550" y="188" font-size="9" fill="#E53935" font-weight="bold">EXIT →</text>

  <!-- ═══ PATIO ═══ -->
  <text x="490" y="448" font-size="11" fill="#8BC34A" font-weight="bold" letter-spacing="1">PATIO</text>
  <rect x="495" y="458" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="518" y="481" text-anchor="middle" font-size="9" fill="#8BC34A">P4</text>
  <rect x="560" y="458" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="583" y="481" text-anchor="middle" font-size="9" fill="#8BC34A">P1</text>

  <rect x="360" y="510" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="383" y="533" text-anchor="middle" font-size="9" fill="#8BC34A">P9</text>
  <rect x="425" y="510" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="448" y="533" text-anchor="middle" font-size="9" fill="#8BC34A">P7</text>
  <rect x="495" y="510" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="518" y="533" text-anchor="middle" font-size="9" fill="#8BC34A">P5</text>
  <rect x="560" y="510" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="583" y="533" text-anchor="middle" font-size="9" fill="#8BC34A">P2</text>

  <rect x="360" y="562" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="383" y="585" text-anchor="middle" font-size="9" fill="#8BC34A">P10</text>
  <rect x="425" y="562" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="448" y="585" text-anchor="middle" font-size="9" fill="#8BC34A">P8</text>
  <rect x="495" y="562" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="518" y="585" text-anchor="middle" font-size="9" fill="#8BC34A">P6</text>
  <rect x="560" y="562" width="46" height="36" rx="3" fill="none" stroke="#8BC34A" stroke-width="1.6"/>
  <text x="583" y="585" text-anchor="middle" font-size="9" fill="#8BC34A">P3</text>

  <!-- ═══ TIKI BAR ═══ -->
  <rect x="85" y="620" width="70" height="22" rx="3" fill="#D4883E" fill-opacity="0.3"
        stroke="#D4883E" stroke-width="1"/>
  <text x="120" y="635" text-anchor="middle" font-size="8" fill="#D4883E" font-weight="bold">TIKI BAR</text>
  <rect x="20" y="615" width="42" height="28" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="41" y="633" text-anchor="middle" font-size="9" fill="#A63D3D">D4</text>
  <rect x="170" y="615" width="42" height="28" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="191" y="633" text-anchor="middle" font-size="9" fill="#A63D3D">D3</text>
  <rect x="225" y="615" width="42" height="28" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="246" y="633" text-anchor="middle" font-size="9" fill="#A63D3D">D2</text>
  <rect x="280" y="615" width="42" height="28" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="301" y="633" text-anchor="middle" font-size="9" fill="#A63D3D">D1</text>
</svg>
"""


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap');

        :root {
            --bg-dark: #1A1A1A;
            --bg-card: #2C2C2C;
            --gold: #C5A55A;
            --gold-light: #D4B96A;
            --sand: #FAF6EE;
            --sand-dark: #E8DFD0;
            --text-primary: #FAF6EE;
            --text-muted: #8B8B8B;
            --success: #5B8C5A;
            --danger: #C25050;
        }

        .stApp {
            font-family: 'Inter', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .block-container {
            padding: 1rem 2rem !important;
            max-width: 1400px;
        }

        /* Brand Header */
        .brand-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 1rem 2rem;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid rgba(197, 165, 90, 0.25);
            margin-bottom: 1rem;
        }

        /* Stats */
        .stats-container { display: flex; gap: 10px; margin: 0.8rem 0; }
        .stat-card {
            flex: 1;
            background: var(--bg-card);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 0.8rem;
            text-align: center;
        }
        .stat-card .stat-num { font-size: 1.6rem; font-weight: 700; }
        .stat-card .stat-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* Zone header */
        .zone-header {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 14px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.75rem;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin: 0.8rem 0 0.4rem 0;
            color: white;
        }

        /* Login */
        .login-box {
            text-align: center;
            padding: 2rem;
            background: var(--bg-card);
            border-radius: 20px;
            border: 1px solid rgba(197, 165, 90, 0.2);
            margin-bottom: 1rem;
        }

        /* Override Streamlit widgets */
        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.78rem !important;
            min-height: 54px !important;
            white-space: pre-wrap !important;
            line-height: 1.3 !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #141414 !important;
            border-right: 1px solid rgba(197, 165, 90, 0.15);
        }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# AUTENTICAZIONE
# ─────────────────────────────────────────────────────────────
def init_session_state():
    defaults = {
        "authenticated": False,
        "username": "",
        "role": "",
        "selected_table": None,
        "show_modal": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def login_page():
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(f"""
        <div class="login-box">
            {LOGO_SVG}
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Username")
            password = st.text_input("Password", type="password", placeholder="Password")
            submitted = st.form_submit_button("Accedi", use_container_width=True, type="primary")
            if submitted:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = USERS[username]["role"]
                    st.rerun()
                else:
                    st.error("Credenziali non valide!")


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


# ─────────────────────────────────────────────────────────────
# DATABASE — Google Sheets
# ─────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    secrets = st.secrets["connections"]["gsheets"]
    creds_dict = {
        "type": secrets["type"],
        "project_id": secrets["project_id"],
        "private_key_id": secrets["private_key_id"],
        "private_key": secrets["private_key"],
        "client_email": secrets["client_email"],
        "client_id": secrets["client_id"],
        "auth_uri": secrets["auth_uri"],
        "token_uri": secrets["token_uri"],
        "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": secrets["client_x509_cert_url"],
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheet():
    client = get_gspread_client()
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(spreadsheet_url)
    try:
        return sh.worksheet("Prenotazioni")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Prenotazioni", rows=1000, cols=len(SHEET_COLUMNS))
        ws.update(range_name="A1", values=[SHEET_COLUMNS])
        return ws


def _read_sheet_fresh():
    """Legge SEMPRE dal foglio Google (nessuna cache). Usato per operazioni di scrittura."""
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        df = pd.DataFrame(data)
        for col in SHEET_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[SHEET_COLUMNS]
        df = df[df["ID"].astype(str).str.strip() != ""]
        # CRITICO: forza TUTTI i valori a stringa per evitare mismatch int/str
        df["Tavolo"] = df["Tavolo"].astype(str).str.strip()
        df["Data"] = df["Data"].astype(str).str.strip()
        df["Fascia_Oraria"] = df["Fascia_Oraria"].astype(str).str.strip()
        df["Cliente"] = df["Cliente"].astype(str).str.strip()
        df["ID"] = df["ID"].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Errore lettura foglio: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


@st.cache_data(ttl=5)
def load_reservations():
    """Lettura con cache breve (5s) per il display. NON usare per scritture."""
    return _read_sheet_fresh()


def _write_sheet(df):
    """Scrive l'intero dataframe sul foglio."""
    try:
        ws = get_worksheet()
        ws.clear()
        data_to_write = [SHEET_COLUMNS] + df[SHEET_COLUMNS].values.tolist()
        ws.update(range_name="A1", values=data_to_write)
        # Invalida la cache IMMEDIATAMENTE
        load_reservations.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def add_reservation(table, cliente, data_str, fascia, fonte):
    df = _read_sheet_fresh()
    # Confronto come stringhe
    conflict = df[
        (df["Tavolo"] == str(table)) &
        (df["Data"] == str(data_str)) &
        (df["Fascia_Oraria"] == str(fascia))
    ]
    if not conflict.empty:
        st.error(f"Tavolo {table} già prenotato per {fascia} del {data_str}!")
        return False

    new_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    new_row = pd.DataFrame([{
        "ID": new_id,
        "Tavolo": str(table),
        "Cliente": str(cliente),
        "Data": str(data_str),
        "Fascia_Oraria": str(fascia),
        "Fonte_Prenotazione": str(fonte),
        "Creato_Da": st.session_state.username,
        "Data_Creazione": now,
        "Ultima_Modifica": now,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    return _write_sheet(df)


def update_reservation(res_id, table, cliente, data_str, fascia, fonte):
    df = _read_sheet_fresh()
    other = df[df["ID"] != str(res_id)]
    conflict = other[
        (other["Tavolo"] == str(table)) &
        (other["Data"] == str(data_str)) &
        (other["Fascia_Oraria"] == str(fascia))
    ]
    if not conflict.empty:
        st.error(f"Tavolo {table} già prenotato per {fascia} del {data_str}!")
        return False

    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    mask = df["ID"] == str(res_id)
    df.loc[mask, "Tavolo"] = str(table)
    df.loc[mask, "Cliente"] = str(cliente)
    df.loc[mask, "Data"] = str(data_str)
    df.loc[mask, "Fascia_Oraria"] = str(fascia)
    df.loc[mask, "Fonte_Prenotazione"] = str(fonte)
    df.loc[mask, "Ultima_Modifica"] = now
    return _write_sheet(df)


def delete_reservation(res_id):
    df = _read_sheet_fresh()
    df = df[df["ID"] != str(res_id)]
    return _write_sheet(df)


def get_reservations_for_date_slot(df, target_date_str, time_slot):
    mask = (df["Data"] == str(target_date_str)) & (df["Fascia_Oraria"] == str(time_slot))
    return df[mask]


# ─────────────────────────────────────────────────────────────
# COMPONENTI UI
# ─────────────────────────────────────────────────────────────
def render_header():
    st.markdown(f"""
    <div class="brand-header">
        {LOGO_SMALL_SVG}
    </div>
    """, unsafe_allow_html=True)


def render_stats(filtered_df):
    total = len(ALL_TABLES)
    occupied = len(filtered_df["Tavolo"].unique())
    free = total - occupied
    pct = int(occupied / total * 100) if total > 0 else 0

    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-num" style="color:var(--text-primary);">{total}</div>
            <div class="stat-label">Totali</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color:var(--success);">{free}</div>
            <div class="stat-label">Liberi</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color:var(--danger);">{occupied}</div>
            <div class="stat-label">Occupati</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color:var(--gold);">{pct}%</div>
            <div class="stat-label">Occupazione</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAPPA TAVOLI (bottoni interattivi)
# ─────────────────────────────────────────────────────────────
def render_table_map(filtered_df):
    # Costruisce mappa occupazione: chiave = stringa tavolo
    occupied_map = {}
    for _, row in filtered_df.iterrows():
        occupied_map[str(row["Tavolo"])] = str(row["Cliente"])

    for zone_name, zone_data in ZONES.items():
        color = zone_data["color"]
        icon = zone_data["icon"]
        tables = zone_data["tables"]

        st.markdown(
            f'<div class="zone-header" style="background:{color};">'
            f'{icon} {zone_name} &mdash; {len(tables)} tavoli</div>',
            unsafe_allow_html=True
        )

        cols_per_row = 5 if len(tables) <= 6 else 6
        rows_needed = (len(tables) + cols_per_row - 1) // cols_per_row

        for row_idx in range(rows_needed):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                table_idx = row_idx * cols_per_row + col_idx
                if table_idx >= len(tables):
                    break
                table_name = tables[table_idx]  # sempre stringa dal dict ZONES
                guest = occupied_map.get(table_name)
                is_occupied = guest is not None

                with cols[col_idx]:
                    if is_occupied:
                        short_name = guest[:12] if len(guest) > 12 else guest
                        label = f"🔴 {table_name}\n{short_name}"
                    else:
                        label = f"🟢 {table_name}"

                    btn_type = "primary" if is_occupied else "secondary"
                    if st.button(
                        label,
                        key=f"tbl_{zone_name}_{table_name}",
                        use_container_width=True,
                        type=btn_type,
                        help=f"Prenotato: {guest}" if is_occupied else f"Tavolo {table_name} — libero",
                    ):
                        st.session_state.selected_table = table_name
                        st.session_state.show_modal = True
                        st.rerun()


# ─────────────────────────────────────────────────────────────
# CRUD PANEL
# ─────────────────────────────────────────────────────────────
def render_crud_panel(filtered_df, selected_date, selected_slot):
    table_name = st.session_state.selected_table
    if not table_name:
        return

    table_res = filtered_df[filtered_df["Tavolo"] == str(table_name)]
    is_occupied = not table_res.empty

    # Zona
    table_zone = ""
    table_color = "#555"
    for zn, zd in ZONES.items():
        if table_name in zd["tables"]:
            table_zone = zn
            table_color = zd["color"]
            break

    status_icon = "🔴" if is_occupied else "🟢"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.6rem;">
        <div style="background:{table_color}; color:white; padding:6px 14px;
                    border-radius:8px; font-weight:700; font-size:1.1rem;">
            {status_icon} Tavolo {table_name}
        </div>
        <div>
            <span style="color:var(--gold); font-weight:600;">{table_zone}</span>
            <span style="color:var(--text-muted); font-size:0.8rem; margin-left:8px;">
                {selected_date.strftime('%d/%m/%Y')} &middot; {selected_slot}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_occupied:
        reservation = table_res.iloc[0]
        _render_occupied(reservation, table_name, selected_date, selected_slot)
    else:
        _render_empty(table_name, selected_date, selected_slot)


def _render_empty(table_name, selected_date, selected_slot):
    is_admin = st.session_state.role == "admin"

    if is_admin:
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.text_input("Nome Cliente *", placeholder="Nome e cognome")
                fonte = st.selectbox("Fonte", BOOKING_SOURCES)
            with col2:
                data_res = st.date_input("Data", value=selected_date, format="DD/MM/YYYY")
                fascia = st.selectbox("Fascia Oraria", TIME_SLOTS,
                                      index=TIME_SLOTS.index(selected_slot))

            col_ok, col_no = st.columns(2)
            with col_ok:
                submitted = st.form_submit_button("Conferma Prenotazione", use_container_width=True, type="primary")
            with col_no:
                cancel = st.form_submit_button("Annulla", use_container_width=True)

            if submitted:
                if not cliente.strip():
                    st.error("Nome obbligatorio!")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(table_name, cliente.strip(), data_str, fascia, fonte):
                        st.success(f"✅ Prenotato: {cliente} → Tavolo {table_name}")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            if cancel:
                st.session_state.show_modal = False
                st.session_state.selected_table = None
                st.rerun()
    else:
        st.info("Tavolo disponibile.")
        if st.button("Chiudi", key="close_empty"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


def _render_occupied(reservation, table_name, selected_date, selected_slot):
    is_admin = st.session_state.role == "admin"

    st.markdown(f"""
    <div style="background:var(--bg-card); border:1px solid rgba(197,165,90,0.3);
                border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.8rem;">
        <div style="color:var(--gold); font-weight:700; font-size:1.05rem;">
            {reservation['Cliente']}
        </div>
        <div style="color:var(--text-muted); font-size:0.75rem; margin-top:3px;">
            {reservation['Fonte_Prenotazione']} &middot; ID: {reservation['ID']}
            &middot; da {reservation['Creato_Da']} il {reservation['Data_Creazione']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_admin:
        tab_edit, tab_delete = st.tabs(["✏️ Modifica", "🗑️ Elimina"])

        with tab_edit:
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cliente = st.text_input("Cliente", value=str(reservation["Cliente"]))
                    fonte_idx = BOOKING_SOURCES.index(reservation["Fonte_Prenotazione"]) \
                        if reservation["Fonte_Prenotazione"] in BOOKING_SOURCES else 0
                    fonte = st.selectbox("Fonte", BOOKING_SOURCES, index=fonte_idx)
                with col2:
                    try:
                        cur_date = datetime.strptime(str(reservation["Data"]), "%d-%m-%Y").date()
                    except (ValueError, TypeError):
                        cur_date = selected_date
                    data_res = st.date_input("Data", value=cur_date, format="DD/MM/YYYY")
                    fascia_idx = TIME_SLOTS.index(reservation["Fascia_Oraria"]) \
                        if reservation["Fascia_Oraria"] in TIME_SLOTS else 0
                    fascia = st.selectbox("Fascia", TIME_SLOTS, index=fascia_idx)

                tavolo_idx = ALL_TABLES.index(table_name) if table_name in ALL_TABLES else 0
                nuovo_tavolo = st.selectbox("Sposta a tavolo", ALL_TABLES, index=tavolo_idx)

                if st.form_submit_button("Salva Modifiche", use_container_width=True, type="primary"):
                    if not cliente.strip():
                        st.error("Nome obbligatorio!")
                    else:
                        data_str = data_res.strftime("%d-%m-%Y")
                        if update_reservation(reservation["ID"], nuovo_tavolo,
                                              cliente.strip(), data_str, fascia, fonte):
                            st.success("✅ Aggiornato!")
                            st.session_state.show_modal = False
                            st.session_state.selected_table = None
                            st.rerun()

        with tab_delete:
            st.warning(f"Eliminare **{reservation['Cliente']}** dal tavolo **{table_name}**?")
            col_del, col_cancel = st.columns(2)
            with col_del:
                if st.button("🗑️ Elimina", type="primary",
                             use_container_width=True, key="btn_del_confirm"):
                    if delete_reservation(reservation["ID"]):
                        st.success("Eliminata!")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            with col_cancel:
                if st.button("Annulla", use_container_width=True, key="btn_del_cancel"):
                    st.session_state.show_modal = False
                    st.session_state.selected_table = None
                    st.rerun()
    else:
        st.info(f"Prenotato da: **{reservation['Cliente']}**")
        if st.button("Chiudi", key="close_occ"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# SIDEBAR — Mappa planimetria (solo riferimento visivo)
# ─────────────────────────────────────────────────────────────
def render_sidebar_map():
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; margin-bottom:6px;">
            {LOGO_SMALL_SVG}
        </div>
        <div style="text-align:center; margin-bottom:10px;">
            <span style="color:#C5A55A; font-weight:700; font-size:0.85rem;
                         letter-spacing:1px;">🗺️ MAPPA SALA</span>
            <div style="color:#8B8B8B; font-size:0.6rem; margin-top:2px;">
                Riferimento posizione tavoli
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(FLOOR_PLAN_SVG, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
def main_dashboard():
    render_sidebar_map()
    render_header()

    # Toolbar
    col_user, col_date, col_slot, col_actions = st.columns([2, 2, 2, 1.5])
    with col_user:
        role_icon = "👑" if st.session_state.role == "admin" else "👁️"
        st.markdown(f"**{role_icon} {st.session_state.username.capitalize()}**")
    with col_date:
        selected_date = st.date_input("Data", value=date.today(),
                                       format="DD/MM/YYYY", key="filter_date")
    with col_slot:
        selected_slot = st.selectbox("Fascia", TIME_SLOTS, key="filter_slot")
    with col_actions:
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("🔄", use_container_width=True, help="Aggiorna dati"):
                load_reservations.clear()
                st.rerun()
        with ac2:
            if st.button("🚪", use_container_width=True, help="Logout"):
                logout()

    # Dati
    df = load_reservations()
    selected_date_str = selected_date.strftime("%d-%m-%Y")
    filtered_df = get_reservations_for_date_slot(df, selected_date_str, selected_slot)

    render_stats(filtered_df)

    # CRUD Panel
    if st.session_state.show_modal and st.session_state.selected_table:
        with st.container(border=True):
            render_crud_panel(filtered_df, selected_date, selected_slot)
        st.divider()

    # Mappa tavoli interattiva
    st.caption("👇 Clicca un tavolo per prenotare o gestire")
    render_table_map(filtered_df)

    # DB completo (admin)
    st.divider()
    if st.session_state.role == "admin":
        with st.expander("📊 Database completo", expanded=False):
            if not df.empty:
                st.dataframe(df.sort_values("Data", ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("Vuoto.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    inject_custom_css()
    init_session_state()
    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()

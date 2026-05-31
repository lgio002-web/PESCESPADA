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
    "Bar": {
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
# LOGO SVG — Fedele al logo circolare Pesce Spada Beach Club
# Colori: oro/sabbia (#C5A55A) su sfondo scuro, cerchio bianco
# ─────────────────────────────────────────────────────────────
LOGO_SVG = """
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
  <circle cx="100" cy="100" r="95" fill="#FAF6EE" stroke="#C5A55A" stroke-width="2"/>
  <!-- Pesce spada stilizzato -->
  <g transform="translate(30, 60)">
    <path d="M5 40 C15 30 35 28 55 32 L105 32 C115 30 125 26 135 20
             C128 30 125 35 120 37 L120 43 C125 45 128 50 135 60
             C125 54 115 50 105 48 L55 48 C35 52 15 50 5 40 Z"
          fill="#C5A55A" opacity="0.9"/>
    <!-- Occhio -->
    <circle cx="45" cy="40" r="3" fill="#2C2C2C"/>
    <!-- Pinna dorsale -->
    <path d="M70 32 L78 18 L86 32" fill="#C5A55A" opacity="0.6"/>
    <!-- Pinna ventrale -->
    <path d="M70 48 L78 62 L86 48" fill="#C5A55A" opacity="0.6"/>
    <!-- Spada/rostro -->
    <line x1="5" y1="40" x2="-8" y2="40" stroke="#C5A55A" stroke-width="2.5" stroke-linecap="round"/>
  </g>
  <!-- Testo PESCE SPADA -->
  <text x="100" y="38" text-anchor="middle" font-family="Georgia, serif"
        font-size="14" font-weight="bold" fill="#2C2C2C" letter-spacing="3">PESCE</text>
  <text x="100" y="54" text-anchor="middle" font-family="Georgia, serif"
        font-size="14" font-weight="bold" fill="#2C2C2C" letter-spacing="3">SPADA</text>
  <!-- Testo BEACH CLUB -->
  <text x="100" y="175" text-anchor="middle" font-family="Georgia, serif"
        font-size="11" fill="#8B7D6B" letter-spacing="4">BEACH CLUB</text>
</svg>
"""

# ─────────────────────────────────────────────────────────────
# MAPPA SVG della sala — fedele al layout fisico
# ─────────────────────────────────────────────────────────────
FLOOR_PLAN_SVG = """
<svg viewBox="0 0 620 900" xmlns="http://www.w3.org/2000/svg"
     style="width:100%; height:auto; background:#1e1e1e; border-radius:12px; padding:8px;">

  <!-- LOGO in alto a sinistra -->
  <text x="10" y="20" font-family="Georgia, serif" font-size="10" fill="#C5A55A"
        font-weight="bold">PESCE SPADA</text>
  <text x="10" y="32" font-family="Inter, sans-serif" font-size="7" fill="#8B8B8B"
        letter-spacing="2">BEACH CLUB</text>

  <!-- ═══ SPIAGGIA (blu) ═══ -->
  <text x="90" y="55" font-family="Inter" font-size="9" fill="#3D7EA6"
        font-weight="bold">SPIAGGIA</text>
  <!-- Riga 1: S6, S7 -->
  <rect x="60" y="62" width="70" height="45" rx="4" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="95" y="88" text-anchor="middle" font-family="Inter" font-size="11" fill="#3D7EA6">S6</text>
  <rect x="200" y="62" width="80" height="50" rx="4" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="240" y="92" text-anchor="middle" font-family="Inter" font-size="11" fill="#3D7EA6">S7</text>
  <!-- Riga 2: S5, S8 -->
  <rect x="60" y="120" width="80" height="45" rx="4" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="100" y="147" text-anchor="middle" font-family="Inter" font-size="11" fill="#3D7EA6">S5</text>
  <rect x="200" y="120" width="80" height="50" rx="4" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="240" y="150" text-anchor="middle" font-family="Inter" font-size="11" fill="#3D7EA6">S8</text>

  <!-- Spiaggia laterale: S4, S3, S2, S1, S0 (colonna sinistra) -->
  <rect x="10" y="240" width="45" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="32" y="260" text-anchor="middle" font-family="Inter" font-size="10" fill="#3D7EA6">S4</text>
  <rect x="35" y="310" width="50" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="60" y="330" text-anchor="middle" font-family="Inter" font-size="10" fill="#3D7EA6">S3</text>
  <rect x="35" y="440" width="50" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="60" y="460" text-anchor="middle" font-family="Inter" font-size="10" fill="#3D7EA6">S2</text>
  <rect x="10" y="540" width="45" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="32" y="560" text-anchor="middle" font-family="Inter" font-size="10" fill="#3D7EA6">S1</text>
  <rect x="10" y="380" width="45" height="30" rx="3" fill="none" stroke="#3D7EA6" stroke-width="1.5"/>
  <text x="32" y="400" text-anchor="middle" font-family="Inter" font-size="10" fill="#3D7EA6">S0</text>

  <!-- Freccia BEACH -->
  <polygon points="10,218 55,210 55,226" fill="none" stroke="#5B8C5A" stroke-width="1.5"/>
  <text x="62" y="222" font-family="Inter" font-size="9" fill="#5B8C5A" font-weight="bold">BEACH</text>

  <!-- ═══ PRIVÉ (azzurro) ═══ -->
  <text x="460" y="55" font-family="Inter" font-size="9" fill="#00BCD4"
        font-weight="bold">PRIVÉ</text>
  <rect x="410" y="62" width="70" height="35" rx="4" fill="none" stroke="#00BCD4" stroke-width="1.5"/>
  <text x="445" y="84" text-anchor="middle" font-family="Inter" font-size="9" fill="#00BCD4">privè2</text>
  <rect x="520" y="62" width="70" height="35" rx="4" fill="none" stroke="#00BCD4" stroke-width="1.5"/>
  <text x="555" y="84" text-anchor="middle" font-family="Inter" font-size="9" fill="#00BCD4">Privè3</text>
  <rect x="410" y="110" width="70" height="35" rx="4" fill="none" stroke="#00BCD4" stroke-width="1.5"/>
  <text x="445" y="132" text-anchor="middle" font-family="Inter" font-size="9" fill="#00BCD4">privè1</text>
  <rect x="520" y="110" width="70" height="35" rx="4" fill="none" stroke="#00BCD4" stroke-width="1.5"/>
  <text x="555" y="132" text-anchor="middle" font-family="Inter" font-size="9" fill="#00BCD4">Privè4</text>

  <!-- ═══ SALA (arancione, rettangolo grande) ═══ -->
  <rect x="110" y="220" width="280" height="400" rx="6" fill="none" stroke="#D4883E" stroke-width="2"/>
  <text x="200" y="215" font-family="Inter" font-size="12" fill="#D4883E"
        font-weight="bold" letter-spacing="3">SALA</text>

  <!-- Tavoli SALA (dentro il rettangolo) -->
  <rect x="135" y="250" width="55" height="45" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="162" y="278" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">4</text>
  <rect x="215" y="250" width="45" height="40" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="238" y="275" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">5</text>
  <rect x="305" y="250" width="55" height="45" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="332" y="278" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">14</text>

  <rect x="135" y="310" width="55" height="35" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="162" y="332" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">3</text>
  <rect x="215" y="320" width="45" height="40" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="238" y="345" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">7</text>

  <rect x="135" y="370" width="55" height="35" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="162" y="392" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">2</text>
  <rect x="215" y="375" width="45" height="40" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="238" y="400" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">8</text>

  <rect x="135" y="440" width="55" height="40" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="162" y="465" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">1</text>
  <rect x="215" y="450" width="50" height="35" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="240" y="472" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">10</text>
  <rect x="305" y="440" width="55" height="45" rx="3" fill="none" stroke="#D4883E" stroke-width="1.2"/>
  <text x="332" y="468" text-anchor="middle" font-family="Inter" font-size="11" fill="#D4883E">11</text>

  <!-- ═══ VERANDA (verde scuro) ═══ -->
  <text x="440" y="280" font-family="Inter" font-size="11" fill="#5B8C5A"
        font-weight="bold" letter-spacing="2">VERANDA</text>
  <rect x="430" y="240" width="60" height="35" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="460" y="262" text-anchor="middle" font-family="Inter" font-size="10" fill="#5B8C5A">V2</text>
  <rect x="430" y="320" width="60" height="40" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="460" y="345" text-anchor="middle" font-family="Inter" font-size="10" fill="#5B8C5A">15</text>
  <rect x="400" y="410" width="65" height="35" rx="3" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="432" y="432" text-anchor="middle" font-family="Inter" font-size="10" fill="#5B8C5A">V1</text>
  <!-- A1, A2, A3 (cerchi verdi) -->
  <circle cx="530" y="430" cx="530" cy="430" r="18" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="530" y="434" text-anchor="middle" font-family="Inter" font-size="9" fill="#5B8C5A">A2</text>
  <circle cx="580" cy="430" r="18" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="580" y="434" text-anchor="middle" font-family="Inter" font-size="9" fill="#5B8C5A">A1</text>
  <circle cx="80" cy="390" r="18" fill="none" stroke="#5B8C5A" stroke-width="1.2"/>
  <text x="80" y="394" text-anchor="middle" font-family="Inter" font-size="9" fill="#5B8C5A">A3</text>

  <!-- O1, O2 (cerchi rossi — bar esterno) -->
  <circle cx="20" cy="465" r="14" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="20" y="469" text-anchor="middle" font-family="Inter" font-size="8" fill="#A63D3D">O1</text>
  <circle cx="20" cy="305" r="14" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="20" y="309" text-anchor="middle" font-family="Inter" font-size="8" fill="#A63D3D">O2</text>

  <!-- EXIT -->
  <text x="540" y="215" font-family="Inter" font-size="9" fill="#C25050"
        font-weight="bold">EXIT →</text>

  <!-- ═══ PATIO (giallo/verde) ═══ -->
  <text x="470" y="485" font-family="Inter" font-size="11" fill="#8BC34A"
        font-weight="bold" letter-spacing="2">PATIO</text>
  <!-- Riga 1: P4, P1 -->
  <rect x="480" y="495" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="505" y="520" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P4</text>
  <rect x="550" y="495" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="575" y="520" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P1</text>
  <!-- Riga 2: P9, P7, P5, P2 -->
  <rect x="340" y="550" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="365" y="575" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P9</text>
  <rect x="410" y="550" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="435" y="575" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P7</text>
  <rect x="480" y="550" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="505" y="575" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P5</text>
  <rect x="550" y="550" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="575" y="575" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P2</text>
  <!-- Riga 3: P10, P8, P6, P3 -->
  <rect x="340" y="605" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="365" y="630" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P10</text>
  <rect x="410" y="605" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="435" y="630" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P8</text>
  <rect x="480" y="605" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="505" y="630" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P6</text>
  <rect x="550" y="605" width="50" height="40" rx="4" fill="none" stroke="#8BC34A" stroke-width="1.8"/>
  <text x="575" y="630" text-anchor="middle" font-family="Inter" font-size="10" fill="#8BC34A">P3</text>

  <!-- ═══ BAR / TIKI BAR ═══ -->
  <rect x="90" y="665" width="65" height="22" rx="3" fill="#D4883E" opacity="0.3" stroke="#D4883E" stroke-width="1"/>
  <text x="122" y="680" text-anchor="middle" font-family="Inter" font-size="8" fill="#D4883E"
        font-weight="bold">TIKI BAR</text>
  <rect x="25" y="660" width="40" height="30" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="45" y="679" text-anchor="middle" font-family="Inter" font-size="9" fill="#A63D3D">D4</text>
  <rect x="168" y="660" width="40" height="30" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="188" y="679" text-anchor="middle" font-family="Inter" font-size="9" fill="#A63D3D">D3</text>
  <rect x="220" y="660" width="40" height="30" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="240" y="679" text-anchor="middle" font-family="Inter" font-size="9" fill="#A63D3D">D2</text>
  <rect x="275" y="660" width="40" height="30" rx="3" fill="none" stroke="#A63D3D" stroke-width="1.2"/>
  <text x="295" y="679" text-anchor="middle" font-family="Inter" font-size="9" fill="#A63D3D">D1</text>

  <!-- Legenda colori -->
  <rect x="10" y="720" width="600" height="1" fill="#333"/>
  <circle cx="25" cy="740" r="5" fill="#3D7EA6"/>
  <text x="36" y="743" font-family="Inter" font-size="8" fill="#aaa">Spiaggia</text>
  <circle cx="105" cy="740" r="5" fill="#00BCD4"/>
  <text x="116" y="743" font-family="Inter" font-size="8" fill="#aaa">Privé</text>
  <circle cx="165" cy="740" r="5" fill="#D4883E"/>
  <text x="176" y="743" font-family="Inter" font-size="8" fill="#aaa">Sala</text>
  <circle cx="215" cy="740" r="5" fill="#5B8C5A"/>
  <text x="226" y="743" font-family="Inter" font-size="8" fill="#aaa">Veranda</text>
  <circle cx="295" cy="740" r="5" fill="#8BC34A"/>
  <text x="306" y="743" font-family="Inter" font-size="8" fill="#aaa">Patio</text>
  <circle cx="355" cy="740" r="5" fill="#A63D3D"/>
  <text x="366" y="743" font-family="Inter" font-size="8" fill="#aaa">Bar</text>
</svg>
"""

# ─────────────────────────────────────────────────────────────
# CSS — Palette sabbia/oro/navy dal logo
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
            gap: 24px;
            padding: 1.2rem 2rem;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid rgba(197, 165, 90, 0.25);
            margin-bottom: 1.2rem;
        }
        .brand-header .brand-text { text-align: left; }
        .brand-header .brand-name {
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--gold);
            letter-spacing: 4px;
            text-transform: uppercase;
        }
        .brand-header .brand-sub {
            font-size: 0.7rem;
            color: var(--text-muted);
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-top: 2px;
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

        /* Zone */
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
        .login-box .brand-name {
            font-family: 'Playfair Display', serif;
            font-size: 1.6rem;
            font-weight: 900;
            color: var(--gold);
            letter-spacing: 3px;
            margin-top: 0.8rem;
        }
        .login-box .brand-sub {
            color: var(--text-muted);
            font-size: 0.7rem;
            letter-spacing: 3px;
        }

        /* Override Streamlit widgets */
        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            min-height: 52px !important;
            white-space: pre-wrap !important;
            line-height: 1.3 !important;
        }

        /* Sidebar map */
        section[data-testid="stSidebar"] {
            background: #1A1A1A !important;
            border-right: 1px solid rgba(197, 165, 90, 0.2);
        }
        section[data-testid="stSidebar"] .block-container {
            padding: 0.5rem !important;
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
            <div class="brand-name">PESCE SPADA</div>
            <div class="brand-sub">Beach Club</div>
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
# Lettura fresca per scritture, cache solo per display
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
        df["Data"] = df["Data"].astype(str)
        return df
    except Exception as e:
        st.error(f"Errore lettura foglio: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


@st.cache_data(ttl=10)
def load_reservations():
    """Lettura con cache breve (10s) per il display. NON usare per scritture."""
    return _read_sheet_fresh()


def _write_sheet(df):
    """Scrive l'intero dataframe sul foglio."""
    try:
        ws = get_worksheet()
        ws.clear()
        data_to_write = [SHEET_COLUMNS] + df[SHEET_COLUMNS].values.tolist()
        ws.update(range_name="A1", values=data_to_write)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def add_reservation(table, cliente, data_str, fascia, fonte):
    # Legge FRESCO per evitare sovrascritture
    df = _read_sheet_fresh()
    # Controlla duplicati
    conflict = df[(df["Tavolo"] == table) & (df["Data"] == data_str) & (df["Fascia_Oraria"] == fascia)]
    if not conflict.empty:
        st.error(f"Tavolo {table} gia' prenotato per {fascia} del {data_str}!")
        return False

    new_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    new_row = pd.DataFrame([{
        "ID": new_id,
        "Tavolo": table,
        "Cliente": cliente,
        "Data": data_str,
        "Fascia_Oraria": fascia,
        "Fonte_Prenotazione": fonte,
        "Creato_Da": st.session_state.username,
        "Data_Creazione": now,
        "Ultima_Modifica": now,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    return _write_sheet(df)


def update_reservation(res_id, table, cliente, data_str, fascia, fonte):
    df = _read_sheet_fresh()
    other = df[df["ID"] != res_id]
    conflict = other[(other["Tavolo"] == table) & (other["Data"] == data_str) & (other["Fascia_Oraria"] == fascia)]
    if not conflict.empty:
        st.error(f"Tavolo {table} gia' prenotato per {fascia} del {data_str}!")
        return False

    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    mask = df["ID"] == res_id
    df.loc[mask, "Tavolo"] = table
    df.loc[mask, "Cliente"] = cliente
    df.loc[mask, "Data"] = data_str
    df.loc[mask, "Fascia_Oraria"] = fascia
    df.loc[mask, "Fonte_Prenotazione"] = fonte
    df.loc[mask, "Ultima_Modifica"] = now
    return _write_sheet(df)


def delete_reservation(res_id):
    df = _read_sheet_fresh()
    df = df[df["ID"] != res_id]
    return _write_sheet(df)


def get_reservations_for_date_slot(df, target_date_str, time_slot):
    mask = (df["Data"] == target_date_str) & (df["Fascia_Oraria"] == time_slot)
    return df[mask]


# ─────────────────────────────────────────────────────────────
# COMPONENTI UI
# ─────────────────────────────────────────────────────────────
def render_header():
    st.markdown(f"""
    <div class="brand-header">
        <div>{LOGO_SVG}</div>
        <div class="brand-text">
            <div class="brand-name">Pesce Spada</div>
            <div class="brand-sub">Beach Club &middot; Prenotazioni</div>
        </div>
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
# MAPPA TAVOLI
# ─────────────────────────────────────────────────────────────
def render_table_map(filtered_df):
    occupied_map = {}
    for _, row in filtered_df.iterrows():
        occupied_map[row["Tavolo"]] = row["Cliente"]

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
                table_name = tables[table_idx]
                guest = occupied_map.get(table_name)
                is_occupied = guest is not None

                with cols[col_idx]:
                    if is_occupied:
                        short_name = guest[:14] if len(guest) > 14 else guest
                        label = f"🔴 {table_name} | {short_name}"
                    else:
                        label = f"🟢 {table_name}"

                    btn_type = "primary" if is_occupied else "secondary"
                    if st.button(
                        label,
                        key=f"tbl_{zone_name}_{table_name}",
                        use_container_width=True,
                        type=btn_type,
                        help=f"{guest}" if is_occupied else f"Tavolo {table_name} libero",
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

    table_res = filtered_df[filtered_df["Tavolo"] == table_name]
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
                submitted = st.form_submit_button("Conferma", use_container_width=True, type="primary")
            with col_no:
                cancel = st.form_submit_button("Annulla", use_container_width=True)

            if submitted:
                if not cliente.strip():
                    st.error("Nome obbligatorio!")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(table_name, cliente.strip(), data_str, fascia, fonte):
                        st.success(f"Prenotato: {cliente} -> {table_name}")
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
        tab_edit, tab_delete = st.tabs(["Modifica", "Elimina"])

        with tab_edit:
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cliente = st.text_input("Cliente", value=reservation["Cliente"])
                    fonte_idx = BOOKING_SOURCES.index(reservation["Fonte_Prenotazione"]) \
                        if reservation["Fonte_Prenotazione"] in BOOKING_SOURCES else 0
                    fonte = st.selectbox("Fonte", BOOKING_SOURCES, index=fonte_idx)
                with col2:
                    try:
                        cur_date = datetime.strptime(reservation["Data"], "%d-%m-%Y").date()
                    except (ValueError, TypeError):
                        cur_date = selected_date
                    data_res = st.date_input("Data", value=cur_date, format="DD/MM/YYYY")
                    fascia_idx = TIME_SLOTS.index(reservation["Fascia_Oraria"]) \
                        if reservation["Fascia_Oraria"] in TIME_SLOTS else 0
                    fascia = st.selectbox("Fascia", TIME_SLOTS, index=fascia_idx)

                tavolo_idx = ALL_TABLES.index(table_name) if table_name in ALL_TABLES else 0
                nuovo_tavolo = st.selectbox("Sposta a tavolo", ALL_TABLES, index=tavolo_idx)

                if st.form_submit_button("Salva", use_container_width=True, type="primary"):
                    if not cliente.strip():
                        st.error("Nome obbligatorio!")
                    else:
                        data_str = data_res.strftime("%d-%m-%Y")
                        if update_reservation(reservation["ID"], nuovo_tavolo,
                                              cliente.strip(), data_str, fascia, fonte):
                            st.success("Aggiornato!")
                            st.session_state.show_modal = False
                            st.session_state.selected_table = None
                            st.rerun()

        with tab_delete:
            st.warning(f"Eliminare **{reservation['Cliente']}** dal tavolo **{table_name}**?")
            col_del, col_cancel = st.columns(2)
            with col_del:
                if st.button("Elimina", type="primary",
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
# DASHBOARD
# ─────────────────────────────────────────────────────────────
def render_sidebar_map():
    """Sidebar con mappa della sala come riferimento visivo."""
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; margin-bottom:8px;">
            <span style="font-family:'Playfair Display',serif; color:#C5A55A;
                         font-weight:700; font-size:1rem; letter-spacing:2px;">
                🗺️ MAPPA SALA
            </span>
            <div style="color:#8B8B8B; font-size:0.65rem; margin-top:2px;">
                Posizione tavoli &mdash; riferimento operatore
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(FLOOR_PLAN_SVG, unsafe_allow_html=True)
        st.markdown("""
        <div style="color:#8B8B8B; font-size:0.6rem; text-align:center; margin-top:6px;">
            Mappa non in scala &mdash; orientamento: spiaggia a sinistra
        </div>
        """, unsafe_allow_html=True)


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
            if st.button("🔄", use_container_width=True, help="Aggiorna"):
                st.cache_data.clear()
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

    # Mappa
    st.caption("Clicca un tavolo per gestire la prenotazione")
    render_table_map(filtered_df)

    # Lista
    st.divider()
    with st.expander(f"Prenotazioni — {selected_slot} {selected_date.strftime('%d/%m/%Y')}", expanded=False):
        if filtered_df.empty:
            st.info("Nessuna prenotazione.")
        else:
            for _, row in filtered_df.iterrows():
                col_info, col_action = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"**{row['Tavolo']}** — {row['Cliente']} "
                        f"*({row['Fonte_Prenotazione']})* `{row['ID']}`"
                    )
                with col_action:
                    if st.session_state.role == "admin":
                        if st.button("🗑️", key=f"qdel_{row['ID']}", help="Elimina"):
                            delete_reservation(row["ID"])
                            st.rerun()

    # DB completo (admin)
    if st.session_state.role == "admin":
        with st.expander("Database completo", expanded=False):
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

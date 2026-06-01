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
from pathlib import Path
import base64
from html import escape
import uuid
import time
from ui_assets import FLOOR_PLAN_SVG as ASSET_FLOOR_PLAN_SVG

# ─────────────────────────────────────────────────────────────
# CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pesce Spada Beach Club",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed",
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

SIDEBAR_TABLE_LAYOUTS = {
    "S6": {"shape": "rect", "x": 40, "y": 42, "w": 55, "h": 35},
    "S7": {"shape": "rect", "x": 130, "y": 42, "w": 65, "h": 38},
    "S5": {"shape": "rect", "x": 40, "y": 86, "w": 55, "h": 35},
    "S8": {"shape": "rect", "x": 130, "y": 86, "w": 65, "h": 38},
    "privè2": {"shape": "rect", "x": 300, "y": 42, "w": 55, "h": 28},
    "Privè3": {"shape": "rect", "x": 380, "y": 42, "w": 55, "h": 28},
    "privè1": {"shape": "rect", "x": 300, "y": 80, "w": 55, "h": 28},
    "Privè4": {"shape": "rect", "x": 380, "y": 80, "w": 55, "h": 28},
    "S4": {"shape": "rect", "x": 6, "y": 172, "w": 36, "h": 24},
    "O2": {"shape": "circle", "cx": 18, "cy": 218, "r": 11},
    "S3": {"shape": "rect", "x": 18, "y": 238, "w": 36, "h": 22},
    "S0": {"shape": "rect", "x": 6, "y": 275, "w": 32, "h": 22},
    "A3": {"shape": "circle", "cx": 55, "cy": 286, "r": 10},
    "O1": {"shape": "circle", "cx": 18, "cy": 340, "r": 11},
    "S2": {"shape": "rect", "x": 18, "y": 360, "w": 36, "h": 22},
    "S1": {"shape": "rect", "x": 6, "y": 420, "w": 36, "h": 24},
    "4": {"shape": "rect", "x": 96, "y": 176, "w": 38, "h": 28},
    "5": {"shape": "rect", "x": 150, "y": 176, "w": 38, "h": 28},
    "14": {"shape": "rect", "x": 218, "y": 176, "w": 46, "h": 32},
    "3": {"shape": "rect", "x": 96, "y": 220, "w": 38, "h": 28},
    "7": {"shape": "rect", "x": 150, "y": 220, "w": 45, "h": 28},
    "2": {"shape": "rect", "x": 96, "y": 262, "w": 38, "h": 28},
    "8": {"shape": "rect", "x": 150, "y": 262, "w": 45, "h": 28},
    "1": {"shape": "rect", "x": 96, "y": 320, "w": 38, "h": 28},
    "10": {"shape": "rect", "x": 140, "y": 335, "w": 38, "h": 24},
    "11": {"shape": "rect", "x": 218, "y": 320, "w": 46, "h": 32},
    "V2": {"shape": "rect", "x": 372, "y": 172, "w": 42, "h": 24},
    "15": {"shape": "rect", "x": 372, "y": 250, "w": 42, "h": 28},
    "V1": {"shape": "rect", "x": 366, "y": 325, "w": 50, "h": 24},
    "A2": {"shape": "circle", "cx": 438, "cy": 370, "r": 12},
    "A1": {"shape": "circle", "cx": 470, "cy": 370, "r": 12},
    "P4": {"shape": "path", "d": "M387 472 Q397 464 407 472 Q417 464 427 472 L427 489 Q417 481 407 489 Q397 481 387 489 Z", "cx": 407, "cy": 478},
    "P1": {"shape": "path", "d": "M463 472 Q473 464 483 472 Q493 464 503 472 L503 489 Q493 481 483 489 Q473 481 463 489 Z", "cx": 483, "cy": 478},
    "P9": {"shape": "path", "d": "M367 507 Q377 499 387 507 Q397 499 407 507 L407 524 Q397 516 387 524 Q377 516 367 524 Z", "cx": 387, "cy": 513},
    "P7": {"shape": "path", "d": "M408 507 Q418 499 428 507 Q438 499 448 507 L448 524 Q438 516 428 524 Q418 516 408 524 Z", "cx": 428, "cy": 513},
    "P5": {"shape": "path", "d": "M449 507 Q459 499 469 507 Q479 499 489 507 L489 524 Q479 516 469 524 Q459 516 449 524 Z", "cx": 469, "cy": 513},
    "P2": {"shape": "path", "d": "M490 507 Q500 499 510 507 Q520 499 530 507 L530 524 Q520 516 510 524 Q500 516 490 524 Z", "cx": 510, "cy": 513},
    "P10": {"shape": "path", "d": "M367 540 Q377 532 387 540 Q397 532 407 540 L407 557 Q397 549 387 557 Q377 549 367 557 Z", "cx": 387, "cy": 546},
    "P8": {"shape": "path", "d": "M408 540 Q418 532 428 540 Q438 532 448 540 L448 557 Q438 549 428 557 Q418 549 408 557 Z", "cx": 428, "cy": 546},
    "P6": {"shape": "path", "d": "M449 540 Q459 532 469 540 Q479 532 489 540 L489 557 Q479 549 469 557 Q459 549 449 557 Z", "cx": 469, "cy": 546},
    "P3": {"shape": "path", "d": "M490 540 Q500 532 510 540 Q520 532 530 540 L530 557 Q520 549 510 557 Q500 549 490 557 Z", "cx": 510, "cy": 546},
    "D4": {"shape": "rect", "x": 22, "y": 552, "w": 70, "h": 24},
    "D3": {"shape": "rect", "x": 128, "y": 552, "w": 70, "h": 24},
    "D2": {"shape": "rect", "x": 204, "y": 552, "w": 70, "h": 24},
    "D1": {"shape": "rect", "x": 280, "y": 552, "w": 70, "h": 24},
}

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
    "Fonte_Prenotazione", "Telefono", "Numero_Persone", "Compleanno",
    "Creato_Da", "Data_Creazione", "Ultima_Modifica"
]

LOGO_FILE = Path(__file__).with_name("logo_pescespada.jpg")
LAYOUT_IMAGE_FILE = Path(__file__).with_name("layout_sidebar.png")

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
<svg viewBox="0 0 460 640" xmlns="http://www.w3.org/2000/svg"
     style="width:100%; height:auto; background:#fafafa; border-radius:8px; border:1px solid #ddd;">

  <!-- Titolo -->
  <text x="230" y="18" text-anchor="middle" font-family="Arial,sans-serif" font-size="9"
        fill="#E53935" font-weight="bold" letter-spacing="1">PRANZO</text>
  <text x="230" y="30" text-anchor="middle" font-family="Arial,sans-serif" font-size="7"
        fill="#333" letter-spacing="1">LAY OUT SUMMER 2026</text>

  <!-- ═══ SPIAGGIA — top (blu) ═══ -->
  <rect x="40" y="42" width="55" height="35" rx="2" fill="none" stroke="#2962FF" stroke-width="1.3"/>
  <text x="67" y="64" text-anchor="middle" font-size="9" fill="#2962FF" font-weight="700">S6</text>
  <rect x="130" y="42" width="65" height="38" rx="2" fill="none" stroke="#2962FF" stroke-width="1.3"/>
  <text x="162" y="66" text-anchor="middle" font-size="9" fill="#2962FF" font-weight="700">S7</text>

  <rect x="40" y="86" width="55" height="35" rx="2" fill="none" stroke="#2962FF" stroke-width="1.3"/>
  <text x="67" y="108" text-anchor="middle" font-size="9" fill="#2962FF" font-weight="700">S5</text>
  <rect x="130" y="86" width="65" height="38" rx="2" fill="none" stroke="#2962FF" stroke-width="1.3"/>
  <text x="162" y="110" text-anchor="middle" font-size="9" fill="#2962FF" font-weight="700">S8</text>

  <!-- ═══ PRIVÉ — top right (azzurro) ═══ -->
  <rect x="300" y="42" width="55" height="28" rx="2" fill="none" stroke="#00BCD4" stroke-width="1.3"/>
  <text x="327" y="60" text-anchor="middle" font-size="7" fill="#00BCD4" font-weight="600">privè2</text>
  <rect x="380" y="42" width="55" height="28" rx="2" fill="none" stroke="#00BCD4" stroke-width="1.3"/>
  <text x="407" y="60" text-anchor="middle" font-size="7" fill="#00BCD4" font-weight="600">Privè3</text>
  <rect x="300" y="80" width="55" height="28" rx="2" fill="none" stroke="#00BCD4" stroke-width="1.3"/>
  <text x="327" y="98" text-anchor="middle" font-size="7" fill="#00BCD4" font-weight="600">privè1</text>
  <rect x="380" y="80" width="55" height="28" rx="2" fill="none" stroke="#00BCD4" stroke-width="1.3"/>
  <text x="407" y="98" text-anchor="middle" font-size="7" fill="#00BCD4" font-weight="600">Privè4</text>

  <!-- BEACH arrow -->
  <polygon points="10,148 40,142 40,154" fill="none" stroke="#4CAF50" stroke-width="1"/>
  <text x="44" y="151" font-size="7" fill="#4CAF50" font-weight="bold">BEACH</text>

  <!-- EXIT arrow -->
  <text x="405" y="148" font-size="7" fill="#E53935" font-weight="bold">EXIT</text>
  <polygon points="435,148 450,142 450,154" fill="none" stroke="#E53935" stroke-width="1"/>

  <!-- ═══ SPIAGGIA laterale sinistra ═══ -->
  <rect x="6" y="172" width="36" height="24" rx="2" fill="none" stroke="#2962FF" stroke-width="1.2"/>
  <text x="24" y="188" text-anchor="middle" font-size="8" fill="#2962FF" font-weight="600">S4</text>

  <!-- O2 -->
  <circle cx="18" cy="218" r="11" fill="none" stroke="#C62828" stroke-width="1.2"/>
  <text x="18" y="222" text-anchor="middle" font-size="7" fill="#C62828" font-weight="600">O2</text>

  <rect x="18" y="238" width="36" height="22" rx="2" fill="none" stroke="#2962FF" stroke-width="1.2"/>
  <text x="36" y="253" text-anchor="middle" font-size="8" fill="#2962FF" font-weight="600">S3</text>

  <rect x="6" y="275" width="32" height="22" rx="2" fill="none" stroke="#2962FF" stroke-width="1.2"/>
  <text x="22" y="290" text-anchor="middle" font-size="8" fill="#2962FF" font-weight="600">S0</text>
  <!-- A3 -->
  <circle cx="55" cy="286" r="10" fill="none" stroke="#4CAF50" stroke-width="1"/>
  <text x="55" y="290" text-anchor="middle" font-size="7" fill="#4CAF50">A3</text>

  <!-- O1 -->
  <circle cx="18" cy="340" r="11" fill="none" stroke="#C62828" stroke-width="1.2"/>
  <text x="18" y="344" text-anchor="middle" font-size="7" fill="#C62828" font-weight="600">O1</text>

  <rect x="18" y="360" width="36" height="22" rx="2" fill="none" stroke="#2962FF" stroke-width="1.2"/>
  <text x="36" y="375" text-anchor="middle" font-size="8" fill="#2962FF" font-weight="600">S2</text>

  <rect x="6" y="420" width="36" height="24" rx="2" fill="none" stroke="#2962FF" stroke-width="1.2"/>
  <text x="24" y="436" text-anchor="middle" font-size="8" fill="#2962FF" font-weight="600">S1</text>

  <!-- ═══ SALA — centro (arancione) ═══ -->
  <rect x="80" y="160" width="200" height="310" rx="3" fill="none" stroke="#E65100" stroke-width="1.8"/>
  <rect x="110" y="150" width="42" height="16" rx="2" fill="#E65100"/>
  <text x="131" y="162" text-anchor="middle" font-size="8" fill="white" font-weight="bold">SALA</text>

  <!-- Riga 1: 4, 5, 14 -->
  <rect x="96" y="176" width="38" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="115" y="194" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">4</text>
  <rect x="150" y="176" width="38" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="169" y="194" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">5</text>
  <rect x="218" y="176" width="46" height="32" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="241" y="196" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">14</text>

  <!-- Riga 2: 3, 7 -->
  <rect x="96" y="220" width="38" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="115" y="238" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">3</text>
  <rect x="150" y="220" width="45" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="172" y="238" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">7</text>

  <!-- Riga 3: 2, 8 -->
  <rect x="96" y="262" width="38" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="115" y="280" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">2</text>
  <rect x="150" y="262" width="45" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="172" y="280" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">8</text>

  <!-- Riga 4: 1, 10, 11 -->
  <rect x="96" y="320" width="38" height="28" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="115" y="338" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">1</text>
  <rect x="140" y="335" width="38" height="24" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="159" y="351" text-anchor="middle" font-size="8" fill="#E65100" font-weight="600">10</text>
  <rect x="218" y="320" width="46" height="32" rx="2" fill="none" stroke="#E65100" stroke-width="1"/>
  <text x="241" y="340" text-anchor="middle" font-size="9" fill="#E65100" font-weight="600">11</text>

  <!-- ═══ VERANDA — destra (blu scuro) ═══ -->
  <rect x="290" y="160" width="130" height="250" rx="3" fill="none" stroke="#1565C0" stroke-width="1.5"/>
  <rect x="330" y="218" width="60" height="16" rx="2" fill="#FFEB3B"/>
  <text x="360" y="230" text-anchor="middle" font-size="7" fill="#333" font-weight="bold">VERANDA</text>

  <rect x="302" y="172" width="42" height="24" rx="2" fill="none" stroke="#1565C0" stroke-width="1"/>
  <text x="323" y="188" text-anchor="middle" font-size="8" fill="#1565C0" font-weight="600">V2</text>

  <rect x="302" y="250" width="42" height="28" rx="2" fill="none" stroke="#1565C0" stroke-width="1"/>
  <text x="323" y="268" text-anchor="middle" font-size="8" fill="#1565C0" font-weight="600">15</text>

  <rect x="290" y="325" width="50" height="24" rx="2" fill="none" stroke="#1565C0" stroke-width="1"/>
  <text x="315" y="341" text-anchor="middle" font-size="8" fill="#1565C0" font-weight="600">V1</text>

  <!-- A1, A2 -->
  <circle cx="370" cy="370" r="12" fill="none" stroke="#4CAF50" stroke-width="1"/>
  <text x="370" y="374" text-anchor="middle" font-size="7" fill="#4CAF50">A2</text>
  <circle cx="410" cy="370" r="12" fill="none" stroke="#4CAF50" stroke-width="1"/>
  <text x="410" y="374" text-anchor="middle" font-size="7" fill="#4CAF50">A1</text>

  <!-- ═══ PATIO — basso destra (verde) ═══ -->
  <rect x="330" y="418" width="45" height="14" rx="2" fill="#CDDC39"/>
  <text x="352" y="429" text-anchor="middle" font-size="7" fill="#333" font-weight="bold">PATIO</text>

  <!-- Riga 1: P4, P1 -->
  <rect x="350" y="438" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="367" y="456" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P4</text>
  <rect x="400" y="438" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="417" y="456" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P1</text>

  <!-- Riga 2: P9, P7, P5, P2 -->
  <rect x="280" y="476" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="297" y="494" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P9</text>
  <rect x="320" y="476" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="337" y="494" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P7</text>
  <rect x="360" y="476" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="377" y="494" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P5</text>
  <rect x="400" y="476" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="417" y="494" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P2</text>

  <!-- Riga 3: P10, P8, P6, P3 -->
  <rect x="280" y="514" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="297" y="532" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P10</text>
  <rect x="320" y="514" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="337" y="532" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P8</text>
  <rect x="360" y="514" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="377" y="532" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P6</text>
  <rect x="400" y="514" width="34" height="28" rx="3" fill="none" stroke="#689F38" stroke-width="1.6"/>
  <text x="417" y="532" text-anchor="middle" font-size="7" fill="#689F38" font-weight="700">P3</text>

  <!-- ═══ TIKI BAR — fondo (arancio) ═══ -->
  <rect x="55" y="560" width="55" height="18" rx="2" fill="#FF8F00" fill-opacity="0.8"/>
  <text x="82" y="572" text-anchor="middle" font-size="7" fill="white" font-weight="bold">TIKI BAR</text>

  <rect x="6" y="556" width="34" height="24" rx="2" fill="none" stroke="#E65100" stroke-width="1.2"/>
  <text x="23" y="572" text-anchor="middle" font-size="8" fill="#E65100" font-weight="600">D4</text>
  <rect x="120" y="556" width="34" height="24" rx="2" fill="none" stroke="#E65100" stroke-width="1.2"/>
  <text x="137" y="572" text-anchor="middle" font-size="8" fill="#E65100" font-weight="600">D3</text>
  <rect x="160" y="556" width="34" height="24" rx="2" fill="none" stroke="#E65100" stroke-width="1.2"/>
  <text x="177" y="572" text-anchor="middle" font-size="8" fill="#E65100" font-weight="600">D2</text>
  <rect x="200" y="556" width="34" height="24" rx="2" fill="none" stroke="#E65100" stroke-width="1.2"/>
  <text x="217" y="572" text-anchor="middle" font-size="8" fill="#E65100" font-weight="600">D1</text>
</svg>
"""

FLOOR_PLAN_SVG = ASSET_FLOOR_PLAN_SVG


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
def inject_custom_css():
    map_fullscreen = st.session_state.get("sidebar_visible", False)
    block_padding = "0.2rem 0.35rem 0.35rem 0.35rem" if map_fullscreen else "1rem 2rem"
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
            padding: BLOCK_PADDING !important;
            max-width: 100% !important;
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

        .zone-card {
            background: #202020;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 0.85rem 0.95rem 1rem 0.95rem;
            margin: 0.7rem 0 1rem 0;
        }

        .zone-subtitle {
            color: var(--text-muted);
            font-size: 0.78rem;
            margin: 0.15rem 0 0.35rem 0;
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
            font-size: 0.8rem !important;
            min-height: 88px !important;
            white-space: pre-wrap !important;
            line-height: 1.3 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            padding: 0.7rem 0.55rem !important;
        }

        .map-shell {
            height: calc(100vh - 0.55rem);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .map-toolbar-spacer {
            min-height: 0.2rem;
        }

        .map-canvas {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .map-panel-title {
            color: #C5A55A;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .map-panel-subtitle {
            color: #8B8B8B;
            font-size: 0.76rem;
            margin-top: 0.15rem;
        }

        .map-panel-note {
            color: #BEB4A1;
            font-size: 0.78rem;
            margin-top: 0.35rem;
        }

        .calendar-bar {
            background: var(--bg-card);
            border: 1px solid rgba(197, 165, 90, 0.18);
            border-radius: 14px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.8rem;
        }

        @media (max-width: 1024px) {
            .block-container {
                padding: 0.8rem 1rem 1rem 1rem !important;
            }

            .zone-card {
                padding: 1rem 1rem 1.15rem 1rem;
                border-radius: 18px;
            }

            .zone-header {
                font-size: 0.82rem;
                padding: 7px 16px;
            }

            .zone-subtitle {
                font-size: 0.84rem;
                margin: 0.35rem 0 0.55rem 0;
            }

            .stButton > button {
                min-height: 110px !important;
                font-size: 0.92rem !important;
                padding: 0.9rem 0.75rem !important;
                border-radius: 12px !important;
            }
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 0.65rem 0.75rem 0.9rem 0.75rem !important;
            }

            .map-panel-title {
                font-size: 0.92rem;
            }

            .map-panel-subtitle,
            .map-panel-note {
                font-size: 0.78rem;
            }

            .stButton > button {
                min-height: 122px !important;
                font-size: 0.98rem !important;
                line-height: 1.35 !important;
            }
        }
    </style>
    """.replace("BLOCK_PADDING", block_padding), unsafe_allow_html=True)


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
        "sidebar_visible": False,
        "filter_date": date.today(),
        "filter_slot": TIME_SLOTS[0],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def login_page():
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.image(str(LOGO_FILE), use_container_width=True)

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
        df["Telefono"] = df["Telefono"].astype(str).replace({"nan": ""}).str.strip()
        df["Numero_Persone"] = df["Numero_Persone"].astype(str).replace({"nan": ""}).str.strip()
        df["Compleanno"] = df["Compleanno"].astype(str).replace({"nan": ""}).str.strip()
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
        # Attende propagazione Google Sheets
        time.sleep(1)
        # Invalida la cache IMMEDIATAMENTE
        load_reservations.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def _sanitize_optional_phone(phone_value):
    if phone_value is None:
        return ""
    phone = str(phone_value).strip()
    return "" if phone.lower() == "nan" else phone


def _sanitize_optional_people(people_value):
    if people_value is None:
        return ""
    people = str(people_value).strip()
    if people.lower() == "nan":
        return ""
    return people if people.isdigit() else ""


def _is_birthday_flag(value):
    return str(value).strip().lower() in {"true", "1", "si", "sì", "yes", "y", "x"}


def _build_table_button_label(table_name, reservation):
    if reservation is None:
        return f"🟢 {table_name}\nDisponibile\n"

    guest = reservation["cliente"]
    short_name = guest[:18] + "..." if len(guest) > 18 else guest
    people = reservation["numero_persone"] or "-"
    birthday_icon = " 🎂" if reservation["compleanno"] else ""
    return f"🔴 {table_name}\n{short_name}{birthday_icon}\n{people} persone"


def _zone_columns_count(tables_count):
    if tables_count <= 4:
        return 2
    if tables_count <= 6:
        return 3
    if tables_count <= 9:
        return 3
    return 4


def build_occupied_map(date_df, selected_slot):
    occupied_map = {}
    for table_name in ALL_TABLES:
        reservation = get_table_reservation_for_date(date_df, table_name, selected_slot)
        if reservation is not None:
            occupied_map[str(table_name)] = {
                "cliente": str(reservation["Cliente"]),
                "fascia": str(reservation["Fascia_Oraria"]),
                "numero_persone": _sanitize_optional_people(reservation.get("Numero_Persone", "")),
                "compleanno": _is_birthday_flag(reservation.get("Compleanno", "")),
            }
    return occupied_map


def _build_sidebar_table_lines(table_name, reservation):
    if reservation is None:
        return [table_name, "LIBERO"]

    guest = reservation["cliente"].strip() or "Prenotato"
    short_name = guest[:11] + "..." if len(guest) > 11 else guest
    if reservation["compleanno"]:
        short_name += " 🎂"
    people = reservation["numero_persone"] or "-"
    return [table_name, short_name, f"{people} pax"]


def build_sidebar_floor_plan_svg(date_df, selected_slot):
    occupied_map = build_occupied_map(date_df, selected_slot)
    svg_parts = [
        """
<svg viewBox="0 0 560 620" xmlns="http://www.w3.org/2000/svg"
     style="width:100%; height:auto; background:#fffdf8; border-radius:10px; border:1px solid #d7cfbf;">
  <rect x="0" y="0" width="560" height="620" rx="10" fill="#fffdf8"/>
  <text x="280" y="22" text-anchor="middle" font-family="Arial,sans-serif" font-size="13"
        fill="#7b6138" font-weight="700" letter-spacing="1">MAPPA DISPONIBILITA'</text>
  <text x="280" y="39" text-anchor="middle" font-family="Arial,sans-serif" font-size="9"
        fill="#6f6f6f">Tavolo · Cliente · Persone · Compleanno</text>

  <rect x="86" y="156" width="206" height="300" rx="5" fill="#fbf7ef" stroke="#d8c7a9" stroke-width="1.6"/>
  <rect x="118" y="146" width="44" height="16" rx="3" fill="#c5975b"/>
  <text x="140" y="158" text-anchor="middle" font-size="8" fill="white" font-weight="700">SALA</text>

  <rect x="360" y="156" width="122" height="250" rx="5" fill="#f2f8f4" stroke="#b9d1ba" stroke-width="1.5"/>
  <rect x="389" y="218" width="64" height="16" rx="3" fill="#5b8c5a"/>
  <text x="421" y="230" text-anchor="middle" font-size="7" fill="white" font-weight="700">VERANDA</text>

  <rect x="360" y="450" width="170" height="110" rx="5" fill="#fff6ec" stroke="#efc28d" stroke-width="1.5"/>
  <rect x="417" y="436" width="58" height="16" rx="3" fill="#d4883e"/>
  <text x="446" y="447" text-anchor="middle" font-size="7" fill="white" font-weight="700">PATIO</text>

  <rect x="18" y="535" width="334" height="62" rx="7" fill="#f9f0f0" stroke="#ddbaba" stroke-width="1.5"/>
  <rect x="136" y="520" width="98" height="18" rx="4" fill="#a63d3d"/>
  <text x="185" y="533" text-anchor="middle" font-size="9" fill="white" font-weight="700">TIKI BAR</text>

  <text x="42" y="150" font-size="7" fill="#4caf50" font-weight="700">BEACH</text>
  <polygon points="10,148 40,142 40,154" fill="none" stroke="#4caf50" stroke-width="1"/>
  <text x="492" y="148" font-size="7" fill="#e53935" font-weight="700">EXIT</text>
  <polygon points="522,148 548,142 548,154" fill="none" stroke="#e53935" stroke-width="1"/>

  <rect x="18" y="598" width="16" height="16" rx="4" fill="#e8fff1" stroke="#169b62" stroke-width="1.8"/>
  <text x="42" y="610" font-size="9" fill="#2d4c3d" font-weight="700">Libero</text>
  <rect x="110" y="598" width="16" height="16" rx="4" fill="#ffe6e2" stroke="#d83f3f" stroke-width="1.8"/>
  <text x="134" y="610" font-size="9" fill="#6c2d2d" font-weight="700">Occupato</text>
"""
    ]

    for table_name, layout in SIDEBAR_TABLE_LAYOUTS.items():
        reservation = occupied_map.get(table_name)
        is_occupied = reservation is not None
        fill = "#FFE6E2" if is_occupied else "#E8FFF1"
        stroke = "#D83F3F" if is_occupied else "#169B62"
        text_color = "#6C2D2D" if is_occupied else "#174E34"
        lines = _build_sidebar_table_lines(table_name, reservation)

        if layout["shape"] == "rect":
            x = layout["x"]
            y = layout["y"]
            w = layout["w"]
            h = layout["h"]
            cx = x + (w / 2)
            cy = y + (h / 2)
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
            )
            font_size = 8 if h >= 32 else 7
        elif layout["shape"] == "circle":
            cx = layout["cx"]
            cy = layout["cy"]
            radius = layout["r"]
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
            )
            font_size = 6
        else:
            cx = layout["cx"]
            cy = layout["cy"]
            svg_parts.append(
                f'<path d="{layout["d"]}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>'
            )
            font_size = 6

        total_lines = len(lines)
        line_gap = font_size + 1
        first_line_y = cy - ((total_lines - 1) * line_gap / 2) + (font_size / 2) - 1
        for idx, line in enumerate(lines):
            weight = "700" if idx == 0 else "600"
            svg_parts.append(
                f'<text x="{cx}" y="{first_line_y + idx * line_gap}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="{font_size}" fill="{text_color}" font-weight="{weight}">{escape(line)}</text>'
            )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _render_svg_image(svg_markup, fullscreen=False):
    svg_base64 = base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    image_style = (
        "width:100%; max-width:1600px; max-height:calc(100vh - 54px); height:100%; display:block; margin:0 auto; object-fit:contain;"
        if fullscreen else
        "width:100%; max-width:1600px; max-height:calc(100vh - 120px); height:auto; display:block; margin:0 auto; object-fit:contain;"
    )
    st.markdown(
        f'<img src="data:image/svg+xml;base64,{svg_base64}" style="{image_style}" />',
        unsafe_allow_html=True,
    )


def add_reservation(table, cliente, data_str, fascia, fonte, telefono="", numero_persone="", compleanno=False):
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
        "Telefono": _sanitize_optional_phone(telefono),
        "Numero_Persone": _sanitize_optional_people(numero_persone),
        "Compleanno": "TRUE" if compleanno else "FALSE",
        "Creato_Da": st.session_state.username,
        "Data_Creazione": now,
        "Ultima_Modifica": now,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    return _write_sheet(df)


def update_reservation(res_id, table, cliente, data_str, fascia, fonte, telefono="", numero_persone="", compleanno=False):
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
    df.loc[mask, "Telefono"] = _sanitize_optional_phone(telefono)
    df.loc[mask, "Numero_Persone"] = _sanitize_optional_people(numero_persone)
    df.loc[mask, "Compleanno"] = "TRUE" if compleanno else "FALSE"
    df.loc[mask, "Ultima_Modifica"] = now
    return _write_sheet(df)


def delete_reservation(res_id):
    df = _read_sheet_fresh()
    df = df[df["ID"] != str(res_id)]
    return _write_sheet(df)


def get_reservations_for_date_slot(df, target_date_str, time_slot):
    mask = (df["Data"] == str(target_date_str)) & (df["Fascia_Oraria"] == str(time_slot))
    return df[mask]


def get_reservations_for_date(df, target_date_str):
    mask = df["Data"] == str(target_date_str)
    return df[mask]


def get_table_reservation_for_date(date_df, table_name, selected_slot):
    table_rows = date_df[date_df["Tavolo"] == str(table_name)]
    if table_rows.empty:
        return None

    exact_slot = table_rows[table_rows["Fascia_Oraria"] == str(selected_slot)]
    if not exact_slot.empty:
        return exact_slot.iloc[0]

    slot_order = {slot: idx for idx, slot in enumerate(TIME_SLOTS)}
    sortable = table_rows.copy()
    sortable["_slot_order"] = sortable["Fascia_Oraria"].map(lambda value: slot_order.get(value, 999))
    sortable = sortable.sort_values(["_slot_order", "Data_Creazione"], ascending=[True, True])
    return sortable.iloc[0]


# ─────────────────────────────────────────────────────────────
# COMPONENTI UI
# ─────────────────────────────────────────────────────────────
def render_header():
    with st.container(border=True):
        col_left, col_center, col_right = st.columns([1, 2.2, 1])
        with col_center:
            st.image(str(LOGO_FILE), use_container_width=True)


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
def render_table_map(date_df, selected_slot):
    occupied_map = build_occupied_map(date_df, selected_slot)

    for zone_name, zone_data in ZONES.items():
        color = zone_data["color"]
        icon = zone_data["icon"]
        tables = zone_data["tables"]
        zone_occupied = sum(1 for table_name in tables if table_name in occupied_map)
        zone_free = len(tables) - zone_occupied

        with st.container(border=True):
            st.markdown(
                f'<div class="zone-header" style="background:{color};">'
                f'{icon} {zone_name} &mdash; {len(tables)} tavoli</div>'
                f'<div class="zone-subtitle">Occupati: {zone_occupied} · Liberi: {zone_free} · Fascia: {selected_slot}</div>',
                unsafe_allow_html=True
            )

            cols_per_row = _zone_columns_count(len(tables))
            rows_needed = (len(tables) + cols_per_row - 1) // cols_per_row

            for row_idx in range(rows_needed):
                cols = st.columns(cols_per_row, gap="medium")
                for col_idx in range(cols_per_row):
                    table_idx = row_idx * cols_per_row + col_idx
                    if table_idx >= len(tables):
                        break
                    table_name = tables[table_idx]  # sempre stringa dal dict ZONES
                    reservation = occupied_map.get(table_name)
                    is_occupied = reservation is not None

                    with cols[col_idx]:
                        label = _build_table_button_label(table_name, reservation)

                        btn_type = "primary" if is_occupied else "secondary"
                        if st.button(
                            label,
                            key=f"tbl_{zone_name}_{table_name}",
                            use_container_width=True,
                            type=btn_type,
                            help=(
                                f"Prenotato: {reservation['cliente']} · {reservation['fascia']}"
                                if is_occupied else f"Tavolo {table_name} — libero"
                            ),
                        ):
                            st.session_state.selected_table = table_name
                            st.session_state.show_modal = True
                            st.rerun()


# ─────────────────────────────────────────────────────────────
# CRUD PANEL
# ─────────────────────────────────────────────────────────────
def render_crud_panel(date_df, selected_date, selected_slot):
    table_name = st.session_state.selected_table
    if not table_name:
        return

    reservation = get_table_reservation_for_date(date_df, table_name, selected_slot)
    is_occupied = reservation is not None

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
        if str(reservation["Fascia_Oraria"]) != str(selected_slot):
            st.info(f"Il tavolo e' occupato nella fascia {reservation['Fascia_Oraria']}.")
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
                telefono = st.text_input("Telefono", placeholder="Facoltativo")
                fonte = st.selectbox("Fonte", BOOKING_SOURCES)
            with col2:
                data_res = st.date_input("Data", value=selected_date, format="DD/MM/YYYY")
                fascia = st.selectbox("Fascia Oraria", TIME_SLOTS,
                                      index=TIME_SLOTS.index(selected_slot))
                numero_persone = st.text_input("Numero persone", placeholder="Solo numeri")
                compleanno = st.checkbox("Compleanno")

            col_ok, col_no = st.columns(2)
            with col_ok:
                submitted = st.form_submit_button("Conferma Prenotazione", use_container_width=True, type="primary")
            with col_no:
                cancel = st.form_submit_button("Annulla", use_container_width=True)

            if submitted:
                if not cliente.strip():
                    st.error("Nome obbligatorio!")
                elif numero_persone.strip() and not numero_persone.strip().isdigit():
                    st.error("Il numero persone deve contenere solo cifre.")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(
                        table_name,
                        cliente.strip(),
                        data_str,
                        fascia,
                        fonte,
                        telefono=telefono,
                        numero_persone=numero_persone,
                        compleanno=compleanno,
                    ):
                        st.success(f"✅ Prenotato: {cliente} → Tavolo {table_name}")
                        load_reservations.clear()
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
    telefono = _sanitize_optional_phone(reservation.get("Telefono", ""))
    numero_persone = _sanitize_optional_people(reservation.get("Numero_Persone", ""))
    compleanno = _is_birthday_flag(reservation.get("Compleanno", ""))
    details = []
    if numero_persone:
        details.append(f"{numero_persone} persone")
    if telefono:
        details.append(f"Tel. {telefono}")
    if compleanno:
        details.append("Compleanno 🎂")
    details_markup = " &middot; ".join(details)

    st.markdown(f"""
    <div style="background:var(--bg-card); border:1px solid rgba(197,165,90,0.3);
                border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.8rem;">
        <div style="color:var(--gold); font-weight:700; font-size:1.05rem;">
            {reservation['Cliente']}{' 🎂' if compleanno else ''}
        </div>
        <div style="color:var(--text-primary); font-size:0.82rem; margin-top:6px;">
            {details_markup if details_markup else 'Nessun dettaglio aggiuntivo'}
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
                    telefono = st.text_input("Telefono", value=telefono)
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
                    numero_persone = st.text_input("Numero persone", value=numero_persone)
                    compleanno = st.checkbox("Compleanno", value=compleanno)

                tavolo_idx = ALL_TABLES.index(table_name) if table_name in ALL_TABLES else 0
                nuovo_tavolo = st.selectbox("Sposta a tavolo", ALL_TABLES, index=tavolo_idx)

                if st.form_submit_button("Salva Modifiche", use_container_width=True, type="primary"):
                    if not cliente.strip():
                        st.error("Nome obbligatorio!")
                    elif numero_persone.strip() and not numero_persone.strip().isdigit():
                        st.error("Il numero persone deve contenere solo cifre.")
                    else:
                        data_str = data_res.strftime("%d-%m-%Y")
                        if update_reservation(reservation["ID"], nuovo_tavolo,
                                              cliente.strip(), data_str, fascia, fonte,
                                              telefono=telefono,
                                              numero_persone=numero_persone,
                                              compleanno=compleanno):
                            st.success("✅ Aggiornato!")
                            load_reservations.clear()
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
                        load_reservations.clear()
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            with col_cancel:
                if st.button("Annulla", use_container_width=True, key="btn_del_cancel"):
                    st.session_state.show_modal = False
                    st.session_state.selected_table = None
                    st.rerun()
    else:
        summary = str(reservation["Cliente"])
        if numero_persone:
            summary += f" · {numero_persone} persone"
        if compleanno:
            summary += " · Compleanno 🎂"
        st.info(f"Prenotato da: **{summary}**")
        if st.button("Chiudi", key="close_occ"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# SIDEBAR — Mappa planimetria (solo riferimento visivo)
# Sidebar inizia chiusa, si apre con il bottone 🗺️
# ─────────────────────────────────────────────────────────────
def render_sidebar_map(date_df, selected_slot):
    if not st.session_state.sidebar_visible:
        return
    with st.container():
        st.markdown('<div class="map-shell">', unsafe_allow_html=True)
        close_spacer, close_col = st.columns([15, 1])
        with close_spacer:
            st.markdown('<div class="map-toolbar-spacer"></div>', unsafe_allow_html=True)
        with close_col:
            st.write("")
            if st.button("✕", key="close_map_panel", use_container_width=True, help="Chiudi mappa"):
                st.session_state.sidebar_visible = False
                st.rerun()
        st.markdown('<div class="map-canvas">', unsafe_allow_html=True)
        _render_svg_image(build_sidebar_floor_plan_svg(date_df, selected_slot), fullscreen=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
def main_dashboard():
    if not st.session_state.sidebar_visible:
        render_header()

    if not st.session_state.sidebar_visible:
        with st.container(border=True):
            col_user, col_date, col_slot, col_actions = st.columns([2, 2.2, 2, 1.7])
            with col_user:
                role_icon = "👑" if st.session_state.role == "admin" else "👁️"
                st.markdown(f"**{role_icon} {st.session_state.username.capitalize()}**  ")
                st.caption("Portale prenotazioni: consulta, inserisci, modifica o cancella")
            with col_date:
                selected_date = st.date_input(
                    "Calendario prenotazioni",
                    value=st.session_state.filter_date,
                    format="DD/MM/YYYY",
                    key="filter_date",
                )
            with col_slot:
                selected_slot = st.selectbox("Fascia oraria", TIME_SLOTS, key="filter_slot")
                st.caption("Seleziona giornata e fascia da visualizzare")
            with col_actions:
                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    if st.button("🗺️", use_container_width=True, help="Apri mappa a schermo pieno"):
                        st.session_state.sidebar_visible = True
                        st.rerun()
                with ac2:
                    if st.button("🔄", use_container_width=True, help="Aggiorna dati"):
                        load_reservations.clear()
                        st.rerun()
                with ac3:
                    if st.button("🚪", use_container_width=True, help="Logout"):
                        logout()
    else:
        selected_date = st.session_state.filter_date
        selected_slot = st.session_state.filter_slot

    # Dati
    df = load_reservations()
    selected_date_str = selected_date.strftime("%d-%m-%Y")
    date_df = get_reservations_for_date(df, selected_date_str)

    render_sidebar_map(date_df, selected_slot)

    if st.session_state.sidebar_visible:
        return

    render_stats(date_df)

    # CRUD Panel
    if st.session_state.show_modal and st.session_state.selected_table:
        with st.container(border=True):
            render_crud_panel(date_df, selected_date, selected_slot)
        st.divider()

    # Mappa tavoli interattiva
    st.caption("👇 Clicca un tavolo per prenotare o gestire. Ogni riquadro mostra tavolo, nome prenotazione e numero persone; il compleanno aggiunge la torta.")
    render_table_map(date_df, selected_slot)

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
    init_session_state()
    inject_custom_css()
    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()

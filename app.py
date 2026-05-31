"""
Pesce Spada Beach Club — Sistema Prenotazioni Tavoli
Streamlit Web App con Google Sheets (gspread diretto)
Design moderno ispirato al brand nautico.
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
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────
ZONES = {
    "Spiaggia": {
        "color": "#1E88E5",
        "icon": "🏖️",
        "tables": ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    },
    "Privé": {
        "color": "#7B1FA2",
        "icon": "✨",
        "tables": ["privè1", "privè2", "Privè3", "Privè4"]
    },
    "Sala": {
        "color": "#F9A825",
        "icon": "🍽️",
        "tables": ["1", "2", "3", "4", "5", "7", "8", "10", "11", "14"]
    },
    "Veranda": {
        "color": "#2E7D32",
        "icon": "🌿",
        "tables": ["V1", "V2", "15", "A1", "A2", "A3"]
    },
    "Patio": {
        "color": "#EF6C00",
        "icon": "☀️",
        "tables": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
    },
    "Bar": {
        "color": "#C62828",
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
# LOGO SVG PESCE SPADA
# ─────────────────────────────────────────────────────────────
LOGO_SVG = """
<svg viewBox="0 0 120 60" xmlns="http://www.w3.org/2000/svg" width="120" height="60">
  <defs>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#D4A843;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#B8860B;stop-opacity:1" />
    </linearGradient>
  </defs>
  <!-- Pesce spada stilizzato -->
  <path d="M10 30 Q20 20 40 25 L85 25 Q95 25 100 22 L115 18 Q105 25 100 28 L100 32 Q105 35 115 42 L100 38 Q95 35 85 35 L40 35 Q20 40 10 30 Z"
        fill="url(#goldGrad)" opacity="0.95"/>
  <!-- Occhio -->
  <circle cx="35" cy="30" r="2.5" fill="#0D1B2A"/>
  <!-- Pinna -->
  <path d="M55 25 L60 15 L65 25 Z" fill="#D4A843" opacity="0.7"/>
  <path d="M55 35 L60 45 L65 35 Z" fill="#D4A843" opacity="0.7"/>
  <!-- Spada -->
  <line x1="10" y1="30" x2="2" y2="30" stroke="#D4A843" stroke-width="1.5" stroke-linecap="round"/>
</svg>
"""

# ─────────────────────────────────────────────────────────────
# CSS DESIGN SYSTEM — NAVY + GOLD
# ─────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap');

        :root {
            --navy-900: #0D1B2A;
            --navy-800: #1B2838;
            --navy-700: #1B3A4B;
            --navy-600: #274C5B;
            --gold-500: #D4A843;
            --gold-400: #E8C468;
            --gold-300: #F0D68A;
            --sand-100: #FDF8F0;
            --sand-200: #F5ECD7;
            --success: #2E7D32;
            --danger: #C62828;
            --occupied: #E53935;
            --free: #43A047;
        }

        .stApp {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(180deg, var(--navy-900) 0%, #0F2136 100%);
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .block-container {
            padding: 1rem 2rem !important;
            max-width: 1400px;
        }

        /* Header Brand */
        .brand-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 1.5rem 2rem;
            background: linear-gradient(135deg, var(--navy-900) 0%, var(--navy-800) 50%, var(--navy-700) 100%);
            border-radius: 16px;
            border: 1px solid rgba(212, 168, 67, 0.3);
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .brand-header .brand-text {
            text-align: left;
        }
        .brand-header .brand-name {
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            font-weight: 900;
            color: var(--gold-500);
            letter-spacing: 3px;
            text-transform: uppercase;
            line-height: 1.1;
        }
        .brand-header .brand-sub {
            font-size: 0.75rem;
            color: rgba(255,255,255,0.5);
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-top: 4px;
        }

        /* Stats */
        .stats-container {
            display: flex;
            gap: 12px;
            margin: 1rem 0;
        }
        .stat-card {
            flex: 1;
            background: rgba(27, 40, 56, 0.8);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .stat-card .stat-num {
            font-size: 1.8rem;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
        }
        .stat-card .stat-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.5);
            margin-top: 4px;
        }

        /* Zone Headers */
        .zone-header {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin: 1rem 0 0.5rem 0;
            color: white;
        }

        /* Login */
        .login-container {
            max-width: 400px;
            margin: 3rem auto;
            padding: 2.5rem;
            background: rgba(27, 40, 56, 0.9);
            border-radius: 20px;
            border: 1px solid rgba(212, 168, 67, 0.2);
            box-shadow: 0 16px 48px rgba(0,0,0,0.4);
        }
        .login-brand {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-brand .name {
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--gold-500);
            letter-spacing: 2px;
        }
        .login-brand .sub {
            color: rgba(255,255,255,0.4);
            font-size: 0.7rem;
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        /* Reservation card in list */
        .res-card {
            background: rgba(27, 40, 56, 0.6);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .res-card .res-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .res-card .res-table {
            background: rgba(212,168,67,0.2);
            color: var(--gold-400);
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.85rem;
        }
        .res-card .res-name {
            color: white;
            font-weight: 600;
        }
        .res-card .res-meta {
            color: rgba(255,255,255,0.4);
            font-size: 0.75rem;
        }

        div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
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
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(f"""
        <div class="login-container">
            <div class="login-brand">
                {LOGO_SVG}
                <div class="name">PESCE SPADA</div>
                <div class="sub">Beach Club &middot; Gestione Tavoli</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Inserisci username")
            password = st.text_input("Password", type="password", placeholder="Inserisci password")
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
# DATABASE (GOOGLE SHEETS)
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


@st.cache_data(ttl=30)
def load_reservations():
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
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


def save_reservations(df):
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


def is_table_booked(table, data_str, fascia):
    """Verifica se il tavolo e' gia' prenotato per data+fascia."""
    df = load_reservations()
    mask = (df["Tavolo"] == table) & (df["Data"] == data_str) & (df["Fascia_Oraria"] == fascia)
    return not df[mask].empty


def add_reservation(table, cliente, data_str, fascia, fonte):
    if is_table_booked(table, data_str, fascia):
        st.error(f"Il tavolo {table} e' gia' prenotato per {fascia} del {data_str}!")
        return False

    df = load_reservations()
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
    return save_reservations(df)


def update_reservation(res_id, table, cliente, data_str, fascia, fonte):
    df = load_reservations()
    other = df[df["ID"] != res_id]
    conflict = other[(other["Tavolo"] == table) & (other["Data"] == data_str) & (other["Fascia_Oraria"] == fascia)]
    if not conflict.empty:
        st.error(f"Il tavolo {table} e' gia' prenotato per {fascia} del {data_str}!")
        return False

    now = datetime.now().strftime("%d-%m-%Y %H:%M")
    mask = df["ID"] == res_id
    df.loc[mask, "Tavolo"] = table
    df.loc[mask, "Cliente"] = cliente
    df.loc[mask, "Data"] = data_str
    df.loc[mask, "Fascia_Oraria"] = fascia
    df.loc[mask, "Fonte_Prenotazione"] = fonte
    df.loc[mask, "Ultima_Modifica"] = now
    return save_reservations(df)


def delete_reservation(res_id):
    df = load_reservations()
    df = df[df["ID"] != res_id]
    return save_reservations(df)


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
            <div class="brand-sub">Beach Club &middot; Sistema Prenotazioni</div>
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
            <div class="stat-num" style="color: white;">{total}</div>
            <div class="stat-label">Tavoli Totali</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: #66BB6A;">{free}</div>
            <div class="stat-label">Disponibili</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: #EF5350;">{occupied}</div>
            <div class="stat-label">Occupati</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: #E8C468;">{pct}%</div>
            <div class="stat-label">Occupazione</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAPPA TAVOLI — GRIGLIA PER ZONA
# ─────────────────────────────────────────────────────────────
def render_table_map(filtered_df):
    """Mappa tavoli divisa per zone con nome ospite visibile."""
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

        cols_per_row = 6
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
                        short_name = guest[:12] if len(guest) > 12 else guest
                        label = f"🔴 {table_name}\n{short_name}"
                    else:
                        label = f"🟢 {table_name}\nLibero"

                    btn_type = "primary" if is_occupied else "secondary"
                    if st.button(
                        label,
                        key=f"tbl_{zone_name}_{table_name}",
                        use_container_width=True,
                        type=btn_type,
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

    # Zona del tavolo
    table_zone = ""
    table_color = "#555"
    for zn, zd in ZONES.items():
        if table_name in zd["tables"]:
            table_zone = zn
            table_color = zd["color"]
            break

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.8rem;">
        <div style="background:{table_color}; color:white; padding:8px 16px;
                    border-radius:8px; font-weight:700; font-size:1.2rem;">
            {'🔴' if is_occupied else '🟢'} {table_name}
        </div>
        <div>
            <div style="color:white; font-weight:600;">{table_zone}</div>
            <div style="color:rgba(255,255,255,0.5); font-size:0.8rem;">
                {selected_date.strftime('%d/%m/%Y')} &middot; {selected_slot}
            </div>
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
        st.markdown("##### Nuova Prenotazione")
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.text_input("Nome Cliente *", placeholder="Nome e cognome")
                fonte = st.selectbox("Fonte Prenotazione", BOOKING_SOURCES)
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
                    st.error("Il nome del cliente e' obbligatorio!")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(table_name, cliente.strip(), data_str, fascia, fonte):
                        st.success(f"Prenotazione confermata: {cliente} -> Tavolo {table_name}")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            if cancel:
                st.session_state.show_modal = False
                st.session_state.selected_table = None
                st.rerun()
    else:
        st.info("Tavolo disponibile per questa fascia oraria.")
        if st.button("Chiudi", key="close_empty"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


def _render_occupied(reservation, table_name, selected_date, selected_slot):
    is_admin = st.session_state.role == "admin"

    # Info prenotazione
    st.markdown(f"""
    <div style="background:rgba(27,40,56,0.8); border:1px solid rgba(212,168,67,0.3);
                border-radius:12px; padding:1rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="color:#E8C468; font-weight:700; font-size:1.1rem;">
                    {reservation['Cliente']}
                </div>
                <div style="color:rgba(255,255,255,0.5); font-size:0.8rem; margin-top:4px;">
                    Fonte: {reservation['Fonte_Prenotazione']} &middot; ID: {reservation['ID']}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="color:rgba(255,255,255,0.6); font-size:0.75rem;">
                    Creato da: {reservation['Creato_Da']}
                </div>
                <div style="color:rgba(255,255,255,0.4); font-size:0.7rem;">
                    {reservation['Data_Creazione']}
                </div>
            </div>
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

                if st.form_submit_button("Salva Modifiche", use_container_width=True, type="primary"):
                    if not cliente.strip():
                        st.error("Nome obbligatorio!")
                    else:
                        data_str = data_res.strftime("%d-%m-%Y")
                        if update_reservation(reservation["ID"], nuovo_tavolo,
                                              cliente.strip(), data_str, fascia, fonte):
                            st.success("Prenotazione aggiornata!")
                            st.session_state.show_modal = False
                            st.session_state.selected_table = None
                            st.rerun()

        with tab_delete:
            st.warning(f"Sei sicuro di voler eliminare la prenotazione di **{reservation['Cliente']}** "
                       f"al tavolo **{table_name}**?")
            st.caption("Questa azione non puo' essere annullata.")

            col_del, col_cancel = st.columns(2)
            with col_del:
                if st.button("Elimina Prenotazione", type="primary",
                             use_container_width=True, key="btn_del_confirm"):
                    if delete_reservation(reservation["ID"]):
                        st.success("Prenotazione eliminata!")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            with col_cancel:
                if st.button("Annulla", use_container_width=True, key="btn_del_cancel"):
                    st.session_state.show_modal = False
                    st.session_state.selected_table = None
                    st.rerun()
    else:
        st.info(f"Prenotazione a nome **{reservation['Cliente']}**")
        if st.button("Chiudi", key="close_occ"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# DASHBOARD PRINCIPALE
# ─────────────────────────────────────────────────────────────
def main_dashboard():
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
        selected_slot = st.selectbox("Fascia Oraria", TIME_SLOTS, key="filter_slot")
    with col_actions:
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("🔄", use_container_width=True, help="Aggiorna dati"):
                st.cache_data.clear()
                st.rerun()
        with ac2:
            if st.button("🚪", use_container_width=True, help="Logout"):
                logout()

    # Carica dati
    df = load_reservations()
    selected_date_str = selected_date.strftime("%d-%m-%Y")
    filtered_df = get_reservations_for_date_slot(df, selected_date_str, selected_slot)

    # Statistiche
    render_stats(filtered_df)

    # Panel CRUD (se tavolo selezionato)
    if st.session_state.show_modal and st.session_state.selected_table:
        with st.container(border=True):
            render_crud_panel(filtered_df, selected_date, selected_slot)
        st.divider()

    # Mappa tavoli
    st.markdown("##### Mappa Tavoli")
    st.caption("Clicca su un tavolo per prenotare, modificare o eliminare")
    render_table_map(filtered_df)

    # Lista prenotazioni attive
    st.divider()
    with st.expander(f"Prenotazioni attive - {selected_slot} {selected_date.strftime('%d/%m/%Y')}", expanded=False):
        if filtered_df.empty:
            st.info("Nessuna prenotazione per questa fascia.")
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
                        if st.button("🗑️", key=f"del_list_{row['ID']}", help="Elimina"):
                            delete_reservation(row["ID"])
                            st.rerun()

    # Database completo (admin)
    if st.session_state.role == "admin":
        with st.expander("Database Completo", expanded=False):
            if not df.empty:
                st.dataframe(
                    df.sort_values("Data", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": st.column_config.TextColumn("ID", width="small"),
                        "Tavolo": st.column_config.TextColumn("Tavolo", width="small"),
                        "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                        "Data": st.column_config.TextColumn("Data", width="small"),
                        "Fascia_Oraria": st.column_config.TextColumn("Fascia", width="small"),
                    }
                )
            else:
                st.info("Database vuoto.")


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

"""
Lido Il Pesce Spada — Sistema Prenotazioni Tavoli
Streamlit Web App con Google Sheets (real-time database)
Layout mappa fedele alla planimetria ufficiale.
"""

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import uuid

# ─────────────────────────────────────────────────────────────
# CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lido Il Pesce Spada — Prenotazioni",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────
COLORS = {
    "primary": "#1B3A5C",
    "secondary": "#F5E6D3",
    "accent": "#2C5F8A",
    "white": "#FFFFFF",
    "occupied": "#C0392B",
    "free": "#27AE60",
    "free_light": "#A8D8B9",
    "text_dark": "#1B3A5C",
    "bg_card": "#F8F4EF",
}

# Tutti i tavoli disponibili (esattamente come nella planimetria)
ALL_TABLES = [
    # Spiaggia Top
    "S6", "S7", "S5", "S8",
    "privè1", "privè2", "Privè3", "Privè4",
    # Spiaggia Laterale
    "S4", "S3", "S2", "S1", "S0",
    "O1", "O2", "A3",
    # Sala
    "1", "2", "3", "4", "5", "7", "8", "10", "11", "14",
    # Veranda
    "V1", "V2", "15", "A1", "A2",
    # Patio
    "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10",
    # Bar
    "D1", "D2", "D3", "D4", "TIKI BAR",
]

TIME_SLOTS = ["Pranzo", "Aperitivo", "Cena"]
BOOKING_SOURCES = ["IG", "TikTok", "Facebook", "Twitter", "Telefono", "SMS", "Altro"]

USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "user": {"password": "user", "role": "user"},
}

SHEET_COLUMNS = [
    "ID", "Tavolo", "Cliente", "Data", "Fascia_Oraria",
    "Fonte_Prenotazione", "Creato_Da", "Data_Creazione", "Ultima_Modifica"
]


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        .stApp { font-family: 'Inter', sans-serif; }

        .main-header {
            text-align: center;
            padding: 1.2rem 0;
            background: linear-gradient(135deg, #1B3A5C 0%, #2C5F8A 100%);
            border-radius: 0 0 16px 16px;
            margin: -1rem -1rem 1.5rem -1rem;
            color: white;
        }
        .main-header h1 { margin:0; font-size:1.8rem; font-weight:700; letter-spacing:1px; }
        .main-header p { margin:0.2rem 0 0 0; font-size:0.9rem; opacity:0.85; }

        .zone-label {
            background: #1B3A5C;
            color: white;
            padding: 0.35rem 0.8rem;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-block;
            margin: 0.8rem 0 0.4rem 0;
        }

        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(27,58,92,0.08);
            text-align: center;
            border-left: 4px solid #2C5F8A;
        }
        .stat-card h3 { margin:0; font-size:1.6rem; color:#1B3A5C; }
        .stat-card p { margin:0.2rem 0 0 0; font-size:0.75rem; color:#666;
                       text-transform:uppercase; letter-spacing:0.5px; }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        div[data-testid="stHorizontalBlock"] { gap: 0.3rem; }
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
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:1.5rem;">
            <h2 style="color:#1B3A5C;">🐟 Lido Il Pesce Spada</h2>
            <p style="color:#666;">Sistema Prenotazioni — Scalea (CS)</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Username")
            password = st.text_input("Password", type="password", placeholder="Password")
            submitted = st.form_submit_button("Accedi", use_container_width=True)
            if submitted:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = USERS[username]["role"]
                    st.rerun()
                else:
                    st.error("Credenziali non valide!")


def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.selected_table = None
    st.session_state.show_modal = False
    st.rerun()


# ─────────────────────────────────────────────────────────────
# DATABASE (GOOGLE SHEETS)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_reservations():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Prenotazioni", usecols=list(range(len(SHEET_COLUMNS))))
        if df is None or df.empty:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        df.columns = SHEET_COLUMNS[:len(df.columns)]
        df = df.dropna(subset=["ID"])
        df["Data"] = df["Data"].astype(str)
        return df
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


def save_reservations(df):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="Prenotazioni", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def add_reservation(table, cliente, data_str, fascia, fonte):
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
    st.markdown("""
    <div class="main-header">
        <h1>🐟 LIDO IL PESCE SPADA</h1>
        <p>Scalea (CS) — Gestione Prenotazioni Tavoli</p>
    </div>
    """, unsafe_allow_html=True)


def render_stats(filtered_df):
    total = len(ALL_TABLES)
    occupied = len(filtered_df["Tavolo"].unique())
    free = total - occupied
    pct = (occupied / total * 100) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{total}</h3><p>Tavoli Totali</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><h3 style="color:#27AE60">{free}</h3><p>Disponibili</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><h3 style="color:#C0392B">{occupied}</h3><p>Occupati</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><h3>{pct:.0f}%</h3><p>Occupazione</p></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAPPA TAVOLI — LAYOUT FEDELE ALLA PLANIMETRIA
# ─────────────────────────────────────────────────────────────
def table_button(table_name, occupied_tables, zone_key):
    """Renderizza un singolo bottone tavolo."""
    is_occ = table_name in occupied_tables
    emoji = "🔴" if is_occ else "🟢"
    btn_type = "primary" if is_occ else "secondary"
    if st.button(f"{emoji} {table_name}", key=f"t_{zone_key}_{table_name}",
                 use_container_width=True, type=btn_type):
        st.session_state.selected_table = table_name
        st.session_state.show_modal = True
        st.rerun()


def render_table_map(occupied_tables):
    """Mappa completa con layout fedele alla planimetria allegata."""

    # ═══════════════ SPIAGGIA TOP ═══════════════
    st.markdown('<span class="zone-label">🏖️ Spiaggia Top</span>', unsafe_allow_html=True)

    # Riga 1: S6, S7, (vuoto x4), privè2, Privè3
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    with c1:
        table_button("S6", occupied_tables, "sptop")
    with c2:
        table_button("S7", occupied_tables, "sptop")
    with c3:
        st.write("")
    with c4:
        st.write("")
    with c5:
        st.write("")
    with c6:
        st.write("")
    with c7:
        table_button("privè2", occupied_tables, "sptop")
    with c8:
        table_button("Privè3", occupied_tables, "sptop")

    # Riga 2: S5, S8, (vuoto x4), privè1, Privè4
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    with c1:
        table_button("S5", occupied_tables, "sptop2")
    with c2:
        table_button("S8", occupied_tables, "sptop2")
    with c3:
        st.write("")
    with c4:
        st.write("")
    with c5:
        st.write("")
    with c6:
        st.write("")
    with c7:
        table_button("privè1", occupied_tables, "sptop2")
    with c8:
        table_button("Privè4", occupied_tables, "sptop2")

    st.markdown("---")

    # ═══════════════ AREA PRINCIPALE: SPIAGGIA | SALA | VERANDA ═══════════════
    beach_col, sala_col, veranda_col = st.columns([1.5, 3, 2])

    # ─── SPIAGGIA LATERALE (colonna sinistra) ───
    with beach_col:
        st.markdown('<span class="zone-label">🏖️ Spiaggia</span>', unsafe_allow_html=True)
        table_button("S4", occupied_tables, "spside")
        table_button("O2", occupied_tables, "spside")
        table_button("S3", occupied_tables, "spside")

        r1, r2 = st.columns(2)
        with r1:
            table_button("S0", occupied_tables, "spside2")
        with r2:
            table_button("A3", occupied_tables, "spside2")

        table_button("O1", occupied_tables, "spside3")
        table_button("S2", occupied_tables, "spside3")
        table_button("S1", occupied_tables, "spside3")

    # ─── SALA (colonna centrale) ───
    with sala_col:
        st.markdown('<span class="zone-label">🍽️ Sala</span>', unsafe_allow_html=True)

        # Riga 1: 4, 5, _, 14
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            table_button("4", occupied_tables, "sala")
        with r2:
            table_button("5", occupied_tables, "sala")
        with r3:
            st.write("")
        with r4:
            table_button("14", occupied_tables, "sala")

        # Riga 2: 3, 7
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            table_button("3", occupied_tables, "sala2")
        with r2:
            table_button("7", occupied_tables, "sala2")
        with r3:
            st.write("")
        with r4:
            st.write("")

        # Riga 3: 2, 8
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            table_button("2", occupied_tables, "sala3")
        with r2:
            table_button("8", occupied_tables, "sala3")
        with r3:
            st.write("")
        with r4:
            st.write("")

        # Riga 4: 1, 10, _, 11
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            table_button("1", occupied_tables, "sala4")
        with r2:
            table_button("10", occupied_tables, "sala4")
        with r3:
            st.write("")
        with r4:
            table_button("11", occupied_tables, "sala4")

    # ─── VERANDA (colonna destra) ───
    with veranda_col:
        st.markdown('<span class="zone-label">🌿 Veranda</span>', unsafe_allow_html=True)
        table_button("V2", occupied_tables, "ver")
        table_button("15", occupied_tables, "ver")
        table_button("V1", occupied_tables, "ver")

        v1, v2 = st.columns(2)
        with v1:
            table_button("A2", occupied_tables, "ver2")
        with v2:
            table_button("A1", occupied_tables, "ver2")

    st.markdown("---")

    # ═══════════════ PATIO ═══════════════
    st.markdown('<span class="zone-label">☀️ Patio</span>', unsafe_allow_html=True)

    # Riga 1: (vuoto x2), P4, P1
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.write("")
    with c2:
        st.write("")
    with c3:
        table_button("P4", occupied_tables, "patio1")
    with c4:
        table_button("P1", occupied_tables, "patio1")
    with c5:
        st.write("")
    with c6:
        st.write("")

    # Riga 2: P9, P7, P5, P2
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        table_button("P9", occupied_tables, "patio2")
    with c2:
        table_button("P7", occupied_tables, "patio2")
    with c3:
        table_button("P5", occupied_tables, "patio2")
    with c4:
        table_button("P2", occupied_tables, "patio2")
    with c5:
        st.write("")
    with c6:
        st.write("")

    # Riga 3: P10, P8, P6, P3
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        table_button("P10", occupied_tables, "patio3")
    with c2:
        table_button("P8", occupied_tables, "patio3")
    with c3:
        table_button("P6", occupied_tables, "patio3")
    with c4:
        table_button("P3", occupied_tables, "patio3")
    with c5:
        st.write("")
    with c6:
        st.write("")

    st.markdown("---")

    # ═══════════════ BAR ═══════════════
    st.markdown('<span class="zone-label">🍹 Bar</span>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        table_button("D4", occupied_tables, "bar")
    with c2:
        table_button("TIKI BAR", occupied_tables, "bar")
    with c3:
        table_button("D3", occupied_tables, "bar")
    with c4:
        table_button("D2", occupied_tables, "bar")
    with c5:
        table_button("D1", occupied_tables, "bar")


# ─────────────────────────────────────────────────────────────
# MODALI CRUD
# ─────────────────────────────────────────────────────────────
def render_crud_modal(filtered_df, selected_date, selected_slot):
    table_name = st.session_state.selected_table
    if not table_name:
        return

    table_res = filtered_df[filtered_df["Tavolo"] == table_name]
    is_occupied = not table_res.empty

    if is_occupied:
        reservation = table_res.iloc[0]
        _modal_occupied(reservation, table_name, selected_date, selected_slot)
    else:
        _modal_empty(table_name, selected_date, selected_slot)


def _modal_empty(table_name, selected_date, selected_slot):
    is_admin = st.session_state.role == "admin"

    st.markdown(f"### 🟢 Tavolo **{table_name}** — Disponibile")
    st.markdown(f"📅 **{selected_date.strftime('%d-%m-%Y')}** | 🕐 **{selected_slot}**")

    if is_admin:
        st.divider()
        with st.form("add_form"):
            st.markdown("#### ➕ Nuova Prenotazione")
            cliente = st.text_input("Nome Cliente *", placeholder="Nome e Cognome")
            fc1, fc2 = st.columns(2)
            with fc1:
                fonte = st.selectbox("Fonte", BOOKING_SOURCES)
            with fc2:
                fascia = st.selectbox("Fascia Oraria", TIME_SLOTS,
                                      index=TIME_SLOTS.index(selected_slot))
            data_res = st.date_input("Data", value=selected_date, format="DD/MM/YYYY")

            bc1, bc2 = st.columns(2)
            with bc1:
                submitted = st.form_submit_button("✅ Conferma", use_container_width=True)
            with bc2:
                cancel = st.form_submit_button("❌ Annulla", use_container_width=True)

            if submitted:
                if not cliente.strip():
                    st.error("Nome cliente obbligatorio!")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(table_name, cliente.strip(), data_str, fascia, fonte):
                        st.success(f"✅ Prenotazione confermata: {cliente} → {table_name}")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            if cancel:
                st.session_state.show_modal = False
                st.session_state.selected_table = None
                st.rerun()
    else:
        st.info("Tavolo libero per questa fascia oraria.")
        if st.button("Chiudi", key="close_empty_modal"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


def _modal_occupied(reservation, table_name, selected_date, selected_slot):
    is_admin = st.session_state.role == "admin"

    st.markdown(f"### 🔴 Tavolo **{table_name}** — Occupato")
    dc1, dc2 = st.columns(2)
    with dc1:
        st.markdown(f"**👤 Cliente:** {reservation['Cliente']}")
        st.markdown(f"**📅 Data:** {reservation['Data']}")
        st.markdown(f"**🕐 Fascia:** {reservation['Fascia_Oraria']}")
    with dc2:
        st.markdown(f"**📱 Fonte:** {reservation['Fonte_Prenotazione']}")
        st.markdown(f"**👨‍💼 Creato da:** {reservation['Creato_Da']}")
        st.markdown(f"**🆔 ID:** `{reservation['ID']}`")

    if is_admin:
        st.divider()
        tab_edit, tab_delete = st.tabs(["✏️ Modifica", "🗑️ Elimina"])

        with tab_edit:
            with st.form("edit_form"):
                cliente = st.text_input("Nome Cliente *", value=reservation["Cliente"])
                ec1, ec2 = st.columns(2)
                with ec1:
                    fonte_idx = BOOKING_SOURCES.index(reservation["Fonte_Prenotazione"]) \
                        if reservation["Fonte_Prenotazione"] in BOOKING_SOURCES else 0
                    fonte = st.selectbox("Fonte", BOOKING_SOURCES, index=fonte_idx)
                with ec2:
                    fascia_idx = TIME_SLOTS.index(reservation["Fascia_Oraria"]) \
                        if reservation["Fascia_Oraria"] in TIME_SLOTS else 0
                    fascia = st.selectbox("Fascia Oraria", TIME_SLOTS, index=fascia_idx)

                try:
                    current_date = datetime.strptime(reservation["Data"], "%d-%m-%Y").date()
                except (ValueError, TypeError):
                    current_date = selected_date
                data_res = st.date_input("Data", value=current_date, format="DD/MM/YYYY")

                tavolo_idx = ALL_TABLES.index(table_name) if table_name in ALL_TABLES else 0
                nuovo_tavolo = st.selectbox("Tavolo", ALL_TABLES, index=tavolo_idx)

                submitted = st.form_submit_button("💾 Salva Modifiche", use_container_width=True)
                if submitted:
                    if not cliente.strip():
                        st.error("Nome cliente obbligatorio!")
                    else:
                        data_str = data_res.strftime("%d-%m-%Y")
                        if update_reservation(reservation["ID"], nuovo_tavolo,
                                              cliente.strip(), data_str, fascia, fonte):
                            st.success("✅ Prenotazione aggiornata!")
                            st.session_state.show_modal = False
                            st.session_state.selected_table = None
                            st.rerun()

        with tab_delete:
            st.warning(f"Eliminare la prenotazione di **{reservation['Cliente']}** "
                       f"al tavolo **{table_name}**?")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("🗑️ Conferma Eliminazione", type="primary",
                             use_container_width=True, key="btn_del"):
                    if delete_reservation(reservation["ID"]):
                        st.success("✅ Prenotazione eliminata!")
                        st.session_state.show_modal = False
                        st.session_state.selected_table = None
                        st.rerun()
            with dc2:
                if st.button("Annulla", use_container_width=True, key="btn_cancel_del"):
                    st.session_state.show_modal = False
                    st.session_state.selected_table = None
                    st.rerun()
    else:
        st.divider()
        st.info("Accesso in sola lettura.")
        if st.button("Chiudi", key="close_occ_modal"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# LISTA PRENOTAZIONI
# ─────────────────────────────────────────────────────────────
def render_reservation_list(filtered_df):
    with st.expander("📋 Lista Prenotazioni (filtro attivo)", expanded=False):
        if filtered_df.empty:
            st.info("Nessuna prenotazione per questa data/fascia.")
        else:
            for _, row in filtered_df.iterrows():
                st.markdown(
                    f"• **{row['Tavolo']}** — {row['Cliente']} "
                    f"({row['Fonte_Prenotazione']}) `{row['ID']}`"
                )


# ─────────────────────────────────────────────────────────────
# DASHBOARD PRINCIPALE
# ─────────────────────────────────────────────────────────────
def main_dashboard():
    render_header()

    # Top bar
    top1, top2, top3 = st.columns([2, 6, 2])
    with top1:
        role_lbl = "👑 Admin" if st.session_state.role == "admin" else "👁️ Viewer"
        st.markdown(f"**{role_lbl}** — {st.session_state.username}")
    with top3:
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    st.divider()

    # Filtri
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        selected_date = st.date_input("📅 Data", value=date.today(),
                                       format="DD/MM/YYYY", key="fdate")
    with f2:
        selected_slot = st.selectbox("🕐 Fascia Oraria", TIME_SLOTS, key="fslot")
    with f3:
        st.markdown("")
        st.markdown("")
        if st.button("🔄 Aggiorna", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Carica dati
    df = load_reservations()
    selected_date_str = selected_date.strftime("%d-%m-%Y")
    filtered_df = get_reservations_for_date_slot(df, selected_date_str, selected_slot)

    # Statistiche
    render_stats(filtered_df)
    st.markdown("")

    # Modale CRUD (se attivo)
    if st.session_state.show_modal and st.session_state.selected_table:
        with st.container(border=True):
            render_crud_modal(filtered_df, selected_date, selected_slot)
        st.divider()

    # Mappa tavoli
    st.markdown("### 🗺️ Mappa Tavoli")
    st.caption("🟢 Disponibile  |  🔴 Occupato — Clicca per interagire")
    occupied = filtered_df["Tavolo"].unique().tolist()
    render_table_map(occupied)

    # Lista prenotazioni
    st.divider()
    render_reservation_list(filtered_df)

    # Database completo (solo admin)
    if st.session_state.role == "admin":
        with st.expander("📊 Database Completo", expanded=False):
            if not df.empty:
                st.dataframe(df.sort_values("Data", ascending=False),
                             use_container_width=True, hide_index=True)
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

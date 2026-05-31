"""
Pesce Spada Beach Club — Sistema Prenotazioni Tavoli
Streamlit Web App con Google Sheets (Service Account auth)
Layout mappa compatto fedele alla planimetria ufficiale.
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
    page_title="Pesce Spada Beach Club — Prenotazioni",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────

ALL_TABLES = [
    "S6", "S7", "S5", "S8",
    "privè1", "privè2", "Privè3", "Privè4",
    "S4", "S3", "S2", "S1", "S0",
    "O1", "O2", "A3",
    "1", "2", "3", "4", "5", "7", "8", "10", "11", "14",
    "V1", "V2", "15", "A1", "A2",
    "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10",
    "D1", "D2", "D3", "D4",
]

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
# CSS — COMPATTO, COLORI DA PLANIMETRIA
# ─────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        .stApp { font-family: 'Inter', sans-serif; }

        .app-header {
            display: flex; align-items: center; justify-content: center; gap: 12px;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, #0a1628 0%, #1a2d4a 100%);
            border-radius: 0 0 12px 12px;
            margin: -1rem -1rem 0.5rem -1rem;
        }
        .app-header .title { color: #e8d5a3; font-size: 1.3rem; font-weight: 700;
                             letter-spacing: 2px; text-transform: uppercase; }
        .app-header .subtitle { color: rgba(255,255,255,0.6); font-size: 0.65rem; letter-spacing: 1px; }

        .stat-row { display: flex; gap: 6px; margin: 0.3rem 0; }
        .stat-box { flex:1; text-align:center; padding:0.3rem; border-radius:8px;
                    border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.03); }
        .stat-box .num { font-size:1.2rem; font-weight:700; }
        .stat-box .lbl { font-size:0.55rem; text-transform:uppercase; letter-spacing:0.5px; opacity:0.6; }

        .zone-tag { display:inline-block; padding:2px 8px; border-radius:4px; font-weight:700;
                    font-size:0.65rem; letter-spacing:1px; text-transform:uppercase; margin:0.3rem 0 0.1rem 0; }
        .zone-spiaggia { background:#2196F3; color:white; }
        .zone-sala { background:#FFC107; color:#333; }
        .zone-veranda { background:#4CAF50; color:white; }
        .zone-patio { background:#8BC34A; color:#333; }
        .zone-bar { background:#FF9800; color:#333; }
        .zone-prive { background:#9C27B0; color:white; }

        div[data-testid="stHorizontalBlock"] { gap: 0.12rem !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container { padding-top:0.5rem !important; padding-bottom:0.5rem !important; }
        div[data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
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
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:1rem;">
            <div style="font-size:2rem; color:#e8d5a3; font-weight:700; letter-spacing:2px;">🐟 PESCE SPADA</div>
            <div style="font-size:0.75rem; color:#888; letter-spacing:1px;">BEACH CLUB — PRENOTAZIONI</div>
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
    for k in ["authenticated", "username", "role", "selected_table", "show_modal"]:
        if k in st.session_state:
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
    """Crea client gspread da st.secrets."""
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
    """Apre il foglio Prenotazioni."""
    client = get_gspread_client()
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(spreadsheet_url)
    return sh.worksheet("Prenotazioni")


@st.cache_data(ttl=30)
def load_reservations():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=SHEET_COLUMNS)
        df = pd.DataFrame(data)
        # Assicura che le colonne corrispondano
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
        # Scrivi header + dati
        data_to_write = [SHEET_COLUMNS] + df[SHEET_COLUMNS].values.tolist()
        ws.update(range_name="A1", values=data_to_write)
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
    <div class="app-header">
        <div>
            <div class="title">🐟 PESCE SPADA</div>
            <div class="subtitle">BEACH CLUB — Gestione Prenotazioni</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_stats(filtered_df):
    total = len(ALL_TABLES)
    occupied = len(filtered_df["Tavolo"].unique())
    free = total - occupied
    pct = (occupied / total * 100) if total > 0 else 0

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box"><div class="num">{total}</div><div class="lbl">Totali</div></div>
        <div class="stat-box"><div class="num" style="color:#4CAF50">{free}</div><div class="lbl">Liberi</div></div>
        <div class="stat-box"><div class="num" style="color:#f44336">{occupied}</div><div class="lbl">Occupati</div></div>
        <div class="stat-box"><div class="num">{pct:.0f}%</div><div class="lbl">Occup.</div></div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAPPA TAVOLI — LAYOUT FEDELE ALLA PLANIMETRIA
# ─────────────────────────────────────────────────────────────
def tb(name, occ, zk):
    """Bottone tavolo compatto."""
    is_occ = name in occ
    emoji = "🔴" if is_occ else "🟢"
    btn_type = "primary" if is_occ else "secondary"
    if st.button(f"{emoji}{name}", key=f"t_{zk}_{name}",
                 use_container_width=True, type=btn_type):
        st.session_state.selected_table = name
        st.session_state.show_modal = True
        st.rerun()


def render_table_map(occ):
    """Mappa compatta fedele alla planimetria."""

    # ══ SPIAGGIA TOP + PRIVÉ ══
    st.markdown('<span class="zone-tag zone-spiaggia">🏖 Spiaggia</span> '
                '<span class="zone-tag zone-prive">Privé</span>',
                unsafe_allow_html=True)
    c = st.columns(8)
    with c[0]: tb("S6", occ, "st1")
    with c[1]: tb("S7", occ, "st1")
    with c[2]: tb("S5", occ, "st2")
    with c[3]: tb("S8", occ, "st2")
    with c[4]: tb("privè2", occ, "pr")
    with c[5]: tb("Privè3", occ, "pr")
    with c[6]: tb("privè1", occ, "pr2")
    with c[7]: tb("Privè4", occ, "pr2")

    # ══ BEACH LAT | SALA | VERANDA ══
    beach_col, sala_col, ver_col = st.columns([1.2, 3, 1.8])

    with beach_col:
        st.markdown('<span class="zone-tag zone-spiaggia">Beach</span>', unsafe_allow_html=True)
        tb("S4", occ, "bl")
        tb("O2", occ, "bl")
        tb("S3", occ, "bl")
        r1, r2 = st.columns(2)
        with r1: tb("S0", occ, "bl2")
        with r2: tb("A3", occ, "bl2")
        tb("O1", occ, "bl3")
        tb("S2", occ, "bl3")
        tb("S1", occ, "bl3")

    with sala_col:
        st.markdown('<span class="zone-tag zone-sala">🍽 Sala</span>', unsafe_allow_html=True)
        r = st.columns(4)
        with r[0]: tb("4", occ, "sa1")
        with r[1]: tb("5", occ, "sa1")
        with r[2]: st.write("")
        with r[3]: tb("14", occ, "sa1")

        r = st.columns(4)
        with r[0]: tb("3", occ, "sa2")
        with r[1]: tb("7", occ, "sa2")

        r = st.columns(4)
        with r[0]: tb("2", occ, "sa3")
        with r[1]: tb("8", occ, "sa3")

        r = st.columns(4)
        with r[0]: tb("1", occ, "sa4")
        with r[1]: tb("10", occ, "sa4")
        with r[2]: st.write("")
        with r[3]: tb("11", occ, "sa4")

    with ver_col:
        st.markdown('<span class="zone-tag zone-veranda">🌿 Veranda</span>', unsafe_allow_html=True)
        tb("V2", occ, "ve")
        tb("15", occ, "ve")
        tb("V1", occ, "ve")
        r1, r2 = st.columns(2)
        with r1: tb("A2", occ, "ve2")
        with r2: tb("A1", occ, "ve2")

    # ══ PATIO ══
    st.markdown('<span class="zone-tag zone-patio">☀ Patio</span>', unsafe_allow_html=True)
    c = st.columns(7)
    with c[3]: tb("P4", occ, "pa1")
    with c[4]: tb("P1", occ, "pa1")

    c = st.columns(7)
    with c[0]: tb("P9", occ, "pa2")
    with c[1]: tb("P7", occ, "pa2")
    with c[2]: tb("P5", occ, "pa2")
    with c[3]: tb("P2", occ, "pa2")

    c = st.columns(7)
    with c[0]: tb("P10", occ, "pa3")
    with c[1]: tb("P8", occ, "pa3")
    with c[2]: tb("P6", occ, "pa3")
    with c[3]: tb("P3", occ, "pa3")

    # ══ BAR ══
    st.markdown('<span class="zone-tag zone-bar">🍹 Bar</span>', unsafe_allow_html=True)
    c = st.columns(6)
    with c[0]: tb("D4", occ, "ba")
    with c[1]:
        st.markdown('<div style="background:#FFC107;color:#333;text-align:center;'
                    'padding:0.4rem;border-radius:6px;font-weight:700;font-size:0.75rem;">'
                    'TIKI BAR</div>', unsafe_allow_html=True)
    with c[2]: tb("D3", occ, "ba")
    with c[3]: tb("D2", occ, "ba")
    with c[4]: tb("D1", occ, "ba")


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

    st.markdown(f"**🟢 {table_name}** — Disponibile · "
                f"{selected_date.strftime('%d-%m-%Y')} · {selected_slot}")

    if is_admin:
        with st.form("add_form"):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                cliente = st.text_input("Cliente *", placeholder="Nome")
            with c2:
                fonte = st.selectbox("Fonte", BOOKING_SOURCES)
            with c3:
                fascia = st.selectbox("Fascia", TIME_SLOTS,
                                      index=TIME_SLOTS.index(selected_slot))
            data_res = st.date_input("Data", value=selected_date, format="DD/MM/YYYY")

            bc1, bc2 = st.columns(2)
            with bc1:
                submitted = st.form_submit_button("✅ Conferma", use_container_width=True)
            with bc2:
                cancel = st.form_submit_button("❌ Annulla", use_container_width=True)

            if submitted:
                if not cliente.strip():
                    st.error("Nome obbligatorio!")
                else:
                    data_str = data_res.strftime("%d-%m-%Y")
                    if add_reservation(table_name, cliente.strip(), data_str, fascia, fonte):
                        st.success(f"✅ {cliente} → {table_name}")
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

    st.markdown(f"**🔴 {table_name}** — {reservation['Cliente']} · "
                f"{reservation['Fonte_Prenotazione']} · `{reservation['ID']}`")

    if is_admin:
        tab_edit, tab_delete = st.tabs(["✏️ Modifica", "🗑️ Elimina"])

        with tab_edit:
            with st.form("edit_form"):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    cliente = st.text_input("Cliente *", value=reservation["Cliente"])
                with c2:
                    fonte_idx = BOOKING_SOURCES.index(reservation["Fonte_Prenotazione"]) \
                        if reservation["Fonte_Prenotazione"] in BOOKING_SOURCES else 0
                    fonte = st.selectbox("Fonte", BOOKING_SOURCES, index=fonte_idx)
                with c3:
                    fascia_idx = TIME_SLOTS.index(reservation["Fascia_Oraria"]) \
                        if reservation["Fascia_Oraria"] in TIME_SLOTS else 0
                    fascia = st.selectbox("Fascia", TIME_SLOTS, index=fascia_idx)

                c4, c5 = st.columns(2)
                with c4:
                    try:
                        cur_date = datetime.strptime(reservation["Data"], "%d-%m-%Y").date()
                    except (ValueError, TypeError):
                        cur_date = selected_date
                    data_res = st.date_input("Data", value=cur_date, format="DD/MM/YYYY")
                with c5:
                    tavolo_idx = ALL_TABLES.index(table_name) if table_name in ALL_TABLES else 0
                    nuovo_tavolo = st.selectbox("Tavolo", ALL_TABLES, index=tavolo_idx)

                submitted = st.form_submit_button("💾 Salva", use_container_width=True)
                if submitted:
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
            st.warning(f"Eliminare **{reservation['Cliente']}** da **{table_name}**?")
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
        st.info("Sola lettura.")
        if st.button("Chiudi", key="close_occ"):
            st.session_state.show_modal = False
            st.session_state.selected_table = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# DASHBOARD PRINCIPALE
# ─────────────────────────────────────────────────────────────
def main_dashboard():
    render_header()

    # Top bar compatta
    c1, c2, c3, c4 = st.columns([1.5, 2, 2, 1.5])
    with c1:
        role_lbl = "👑 Admin" if st.session_state.role == "admin" else "👁 Viewer"
        st.markdown(f"**{role_lbl}** — {st.session_state.username}")
    with c2:
        selected_date = st.date_input("📅 Data", value=date.today(),
                                       format="DD/MM/YYYY", key="fdate",
                                       label_visibility="collapsed")
    with c3:
        selected_slot = st.selectbox("Fascia", TIME_SLOTS, key="fslot",
                                      label_visibility="collapsed")
    with c4:
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("🔄", use_container_width=True, help="Aggiorna"):
                st.cache_data.clear()
                st.rerun()
        with bc2:
            if st.button("🚪", use_container_width=True, help="Logout"):
                logout()

    # Carica dati
    df = load_reservations()
    selected_date_str = selected_date.strftime("%d-%m-%Y")
    filtered_df = get_reservations_for_date_slot(df, selected_date_str, selected_slot)

    # Statistiche compatte
    render_stats(filtered_df)

    # Modale CRUD sopra la mappa per velocità
    if st.session_state.show_modal and st.session_state.selected_table:
        with st.container(border=True):
            render_crud_modal(filtered_df, selected_date, selected_slot)

    # Mappa tavoli
    st.caption("🟢 Libero · 🔴 Occupato — clicca per interagire")
    occupied = filtered_df["Tavolo"].unique().tolist()
    render_table_map(occupied)

    # Lista prenotazioni
    with st.expander("📋 Prenotazioni", expanded=False):
        if filtered_df.empty:
            st.info("Nessuna prenotazione.")
        else:
            for _, row in filtered_df.iterrows():
                st.markdown(f"• **{row['Tavolo']}** — {row['Cliente']} "
                            f"({row['Fonte_Prenotazione']}) `{row['ID']}`")

    # DB completo (admin)
    if st.session_state.role == "admin":
        with st.expander("📊 Database", expanded=False):
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

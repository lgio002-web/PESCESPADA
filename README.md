# 🐟 Lido Il Pesce Spada — Sistema Prenotazioni

App Streamlit per la gestione prenotazioni tavoli del Lido Il Pesce Spada, Scalea (CS).

## Setup

### 1. Google Sheet
1. Crea un Google Sheet con un foglio chiamato **"Prenotazioni"**
2. Nella prima riga inserisci le intestazioni:
   ```
   ID | Tavolo | Cliente | Data | Fascia_Oraria | Fonte_Prenotazione | Creato_Da | Data_Creazione | Ultima_Modifica
   ```

### 2. Service Account Google
1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un progetto (o usa uno esistente)
3. Abilita **Google Sheets API** e **Google Drive API**
4. Crea una **Service Account** e scarica il file JSON delle credenziali
5. Condividi il Google Sheet con l'email della service account (permessi Editor)

### 3. Deploy su Streamlit Community Cloud
1. Carica il repo su GitHub (senza `secrets.toml`!)
2. Vai su [share.streamlit.io](https://share.streamlit.io)
3. Collega il repository e seleziona `app.py`
4. Nelle **Settings → Secrets**, incolla il contenuto del `secrets.toml` con le credenziali reali

### 4. Formato Secrets (da incollare su Streamlit Cloud)
```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/IL_TUO_ID/edit"
type = "service_account"

[connections.gsheets.service_account]
type = "service_account"
project_id = "il-tuo-progetto"
private_key_id = "abc123"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "nome@progetto.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

## Credenziali App

| Ruolo | Username | Password | Permessi |
|-------|----------|----------|----------|
| Admin | `admin`  | `admin`  | CRUD completo |
| Viewer | `user`  | `user`   | Solo lettura |

## Struttura File
```
├── app.py                          # Applicazione principale
├── requirements.txt                # Dipendenze Python
├── .streamlit/
│   └── secrets.toml.example        # Template secrets (NON committare il vero secrets.toml)
└── README.md
```

## .gitignore consigliato
```
.streamlit/secrets.toml
__pycache__/
*.pyc
```

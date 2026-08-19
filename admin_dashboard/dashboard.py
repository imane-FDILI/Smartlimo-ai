import os
import sys
import hashlib
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text
from streamlit_cookies_controller import CookieController

# =========================================================================
# 0. CONNEXION À LA BASE (réutilise le backend du projet)
# -------------------------------------------------------------------------
#  On ajoute le dossier backend au chemin Python pour pouvoir importer
#  app.database (qui lit ton DATABASE_URL depuis le .env).
# =========================================================================
BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.append(os.path.abspath(BACKEND_PATH))

DB_OK = True
DB_ERROR = ""
try:
    from app.database import SessionLocal, engine  # noqa
except Exception as e:  # si l'import échoue, on l'affichera proprement
    DB_OK = False
    DB_ERROR = str(e)

# =========================================================================
# 1. CONFIG
# =========================================================================
st.set_page_config(page_title="smartlimo-dashboard",
                   page_icon=":material/directions_car:",
                   layout="wide", initial_sidebar_state="expanded")
cookies = CookieController()

# =========================================================================
# 2. CSS
# =========================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

:root{
  --gold:#c99f2e; --gold2:#b8901f; --goldsoft:#f7f0dc;
  --ink:#1c1c1c; --muted:#8b8f98; --line:#eceef1;
}
.mi{ font-family:'Material Symbols Rounded'; font-weight:400; font-style:normal;
  font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;
  line-height:1; vertical-align:middle; display:inline-flex; font-size:18px; }

.stApp{ background:#141414; }
[data-testid="stHeader"]{ display:none; }
#MainMenu, footer{ visibility:hidden; }
.block-container{ background:#fff; border-radius:20px;
  padding:24px 28px 32px 28px !important; margin-top:14px; max-width:1220px; }

/* FIX : texte lisible sur le fond blanc (login + contenu) */
.block-container, .block-container p, .block-container label,
.block-container h1, .block-container h2, .block-container h3,
.block-container span{ color:#1c1c1c !important; }
.block-container input{ color:#1c1c1c !important; background:#fff !important;
  border:1px solid #d9dce1 !important; }

/* SIDEBAR */
section[data-testid="stSidebar"]{ background:#1b1b1b; }
section[data-testid="stSidebar"] *{ color:#a7abb4; }
.s-brand{ display:flex;align-items:center;gap:10px;padding:2px 2px 20px; }
.s-logo{ width:34px;height:34px;border-radius:9px;display:flex;align-items:center;
  justify-content:center;background:linear-gradient(135deg,var(--gold),var(--gold2)); }
.s-logo .mi{ color:#1c1c1c;font-size:20px; }
.s-name{ color:#fff!important;font-weight:700;font-size:16px; }
.s-name span{ color:var(--gold)!important; }
.s-user{ display:flex;align-items:center;gap:10px;padding:12px 4px;
  border-top:1px solid #2a2a2a;margin-top:18px; }
.s-av{ width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#5a6270,#3a3f4a);
  display:flex;align-items:center;justify-content:center;color:#fff!important;
  font-size:13px;font-weight:700;flex-shrink:0; }
.s-uname{ color:#fff!important;font-size:13px;font-weight:600;line-height:1.2; }
.s-urole{ color:#7f838c!important;font-size:11px; }
section[data-testid="stSidebar"] .stButton>button{
  background:transparent;border:1px solid #2a2a2a;color:#a7abb4;border-radius:9px;
  width:100%;font-size:14px;text-align:left; }
section[data-testid="stSidebar"] .stButton>button:hover{ background:#242424;color:#fff; }
section[data-testid="stSidebar"] .stButton>button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"]{
  background:linear-gradient(135deg,var(--gold),var(--gold2))!important;
  color:#1c1c1c!important;border:none!important;font-weight:600!important; }

/* HERO */
.hero{ background:linear-gradient(135deg,var(--gold2),var(--gold) 60%,#d8b24a);
  border-radius:14px;padding:26px 30px;color:#fff;margin-bottom:18px; }
.hero h1{ font-size:26px;font-weight:800;margin:0 0 6px;color:#fff!important; }
.hero p{ font-size:13px;opacity:.92;margin:0;display:flex;align-items:center;gap:6px;color:#fff!important; }
.hero p .mi{ font-size:16px; }

/* STAT CARDS */
.stats{ display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:16px; }
.stat{ background:#fff;border:1px solid var(--line);border-radius:13px;padding:16px; }
.stat .top{ display:flex;justify-content:space-between;align-items:center;
  color:var(--muted)!important;font-size:12.5px;font-weight:600;margin-bottom:10px; }
.stat .ic{ width:26px;height:26px;border-radius:7px;background:var(--goldsoft);
  display:flex;align-items:center;justify-content:center; }
.stat .ic .mi{ font-size:15px;color:var(--gold2); }
.stat .val{ font-size:24px;font-weight:800;color:var(--ink); }

/* CHARTS */
.charts{ display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px; }
.card{ background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px; }
.card .head{ display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }
.card .head .t{ font-size:15px;font-weight:700;color:var(--ink); }
.card .head .s{ font-size:11px;color:var(--muted); }

.vbars{ display:flex;align-items:flex-end;gap:14px;height:180px;padding-left:34px;position:relative; }
.yaxis{ position:absolute;left:0;top:0;bottom:22px;display:flex;flex-direction:column;
  justify-content:space-between;font-size:10px;color:#b7bcc4; }
.vbar{ flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%; }
.vbar .bar{ width:60%;background:linear-gradient(180deg,var(--gold),var(--gold2));border-radius:5px 5px 0 0;min-height:2px; }
.vbar .lab{ font-size:10.5px;color:var(--muted);margin-top:8px; }
.vbar .vval{ font-size:11px;font-weight:700;color:var(--gold2);margin-bottom:4px; }

.hbar{ display:flex;align-items:center;gap:12px;margin-bottom:12px; }
.hbar .name{ width:110px;font-size:12.5px;color:#4b4f57;flex-shrink:0; }
.hbar .track{ flex:1;height:15px;background:#f3f0e7;border-radius:8px;overflow:hidden; }
.hbar .fill{ height:100%;background:linear-gradient(90deg,var(--gold),var(--gold2));border-radius:8px; }
.hbar .v{ width:30px;font-size:12.5px;font-weight:700;color:#3a3e46;text-align:right; }

/* BREAKDOWN */
.bd-row{ display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px; }
.bd{ display:flex;align-items:center;gap:14px;background:#fff;border:1px solid var(--line);
  border-radius:13px;padding:16px 18px; }
.bd .ic{ width:34px;height:34px;border-radius:9px;background:var(--goldsoft);
  display:flex;align-items:center;justify-content:center; }
.bd .ic .mi{ font-size:18px;color:var(--gold2); }
.bd .lab{ font-size:12px;color:var(--muted); }
.bd .amt{ font-size:19px;font-weight:800;color:var(--ink); }

/* TABLE */
.list-title{ font-size:16px;font-weight:700;color:var(--ink);margin:6px 0 12px; }
table.ops{ width:100%;border-collapse:collapse; }
table.ops th{ font-size:11.5px;color:var(--muted);text-align:left;font-weight:600;
  padding:10px 12px;border-bottom:1px solid var(--line); }
table.ops th:last-child, table.ops td:last-child{ text-align:right; }
table.ops td{ padding:14px 12px;font-size:13px;border-bottom:1px solid var(--line);color:#3a3e46; }
table.ops td.dest{ font-weight:700;color:var(--ink); }
table.ops td.muted{ color:var(--muted); }
.yes{ color:var(--gold2);font-weight:600; } .no{ color:var(--muted); }
.total{ font-weight:700;color:var(--ink); }
.badge{ padding:4px 12px;border-radius:999px;font-size:11.5px;font-weight:600; }
.b-ok{ background:#dff5e6;color:#1f9d55; }
.b-wait{ background:#fdf3d6;color:#b9861f; }
.b-no{ background:#fde3e3;color:#d64545; }

div[data-testid="stDownloadButton"] button{ background:#fff;border:1px solid var(--gold);
  color:var(--gold2);border-radius:9px;font-weight:600;font-size:12.5px;padding:7px 14px; }
div[data-testid="stDownloadButton"] button:hover{ background:var(--goldsoft); }

/* === CORRECTION 1 : bouton "Se connecter" lisible (blanc sur doré) === */
.block-container div[data-testid="stFormSubmitButton"] button{
  background:linear-gradient(135deg,var(--gold),var(--gold2)) !important;
  color:#fff !important;
  border:none !important;
  font-weight:600 !important;
}

/* === CORRECTION 2 : icône œil (afficher le mot de passe) visible === */
.block-container .stTextInput button{
  background:transparent !important;
  border:none !important;
}
.block-container .stTextInput button svg,
.block-container .stTextInput button svg path{
  fill:#1c1c1c !important;
  stroke:#1c1c1c !important;
  color:#1c1c1c !important;
  opacity:1 !important;
}
/* Rendre le petit bouton de l'oeil doré au lieu de noir */
.stTextInput [data-baseweb="input"] button,
.stTextInput [data-baseweb="base-input"] button{
  background:var(--gold) !important;
  border-radius:6px !important;
}
.stTextInput [data-baseweb="input"] button *,
.stTextInput [data-baseweb="base-input"] button *{
  color:#fff !important;
  fill:#fff !important;
}
/* Masquer complètement le bouton oeil du champ mot de passe */
.stTextInput button{ display:none !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# 3. LOGIN
# =========================================================================
ADMINS = {"admin": hashlib.sha256("admin123".encode()).hexdigest()}
ADMIN_PROFILE = {"name": "John Martinez", "role": "Admin"}


def check_login(u, p):
    return ADMINS.get(u) == hashlib.sha256(p.encode()).hexdigest()

AUTH_TOKEN = hashlib.sha256("smartlimo-admin-2026".encode()).hexdigest()[:16]

def login_gate():
    # 1) déjà connectée dans cette session ?
    if st.session_state.get("auth"):
        return True
    # 2) sinon, l'URL contient-elle le bon jeton ? (survit au F5)
    if st.query_params.get("auth") == AUTH_TOKEN:
        st.session_state["auth"] = True
        return True

    c = st.columns([1, 1.2, 1])[1]
    with c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### :material/lock: Espace administrateur")
        st.caption("Connecte-toi pour accéder au tableau de bord.")
        with st.form("login"):
            u = st.text_input("Identifiant")
            p = st.text_input("Mot de passe", type="password")
            ok = st.form_submit_button("Se connecter", use_container_width=True)
        if ok:
            if check_login(u, p):
                st.session_state["auth"] = True
                st.query_params["auth"] = AUTH_TOKEN   # <-- écrit le jeton dans l'URL
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
        st.caption("Démo : admin / admin123")
    return False

# =========================================================================
# 4. ACCÈS AUX VRAIES DONNÉES
# -------------------------------------------------------------------------
#  Chaque fonction lit la base et renvoie des structures simples.
#  @st.cache_data évite de requêter la base à chaque clic (rafraîchi 60 s).
# =========================================================================
def _vehicle_name_column():
    """Détecte automatiquement la colonne 'nom' de la table vehicles."""
    try:
        cols = [c["name"] for c in inspect(engine).get_columns("vehicles")]
    except Exception:
        return None
    for candidate in ("name", "type", "vehicle_type", "label", "model", "category"):
        if candidate in cols:
            return candidate
    # sinon, première colonne texte qui n'est pas l'id
    return None


@st.cache_data(ttl=60)
def load_reservations():
    """Renvoie un DataFrame des réservations avec le nom du véhicule si possible."""
    vcol = _vehicle_name_column()
    if vcol:
        sql = f"""
            SELECT r.id, r.dropoff_location, r.pickup_date, r.pickup_time,
                   COALESCE(v.{vcol}::text, r.vehicle_id::text) AS vehicle,
                   r.child_seat_requested, r.price, r.status, r.created_at
            FROM reservations r
            LEFT JOIN vehicles v ON v.id = r.vehicle_id
            ORDER BY r.created_at DESC
        """
    else:
        sql = """
            SELECT r.id, r.dropoff_location, r.pickup_date, r.pickup_time,
                   r.vehicle_id::text AS vehicle,
                   r.child_seat_requested, r.price, r.status, r.created_at
            FROM reservations r
            ORDER BY r.created_at DESC
        """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def compute_stats(df):
    total = len(df)
    revenue = float(df["price"].fillna(0).sum())
    pending = int((df["status"].str.lower() == "pending").sum()) if total else 0
    confirmed = int((df["status"].str.lower() == "confirmed").sum()) if total else 0
    # taux de confirmation sur les non-annulées
    non_cancelled = int((df["status"].str.lower() != "cancelled").sum()) if total else 0
    conf = round(confirmed / non_cancelled * 100) if non_cancelled else 0
    child = int(df["child_seat_requested"].fillna(False).sum()) if total else 0
    return {"total": total, "revenue": revenue, "pending": pending,
            "conf": conf, "child": child}


def revenue_by_day(df, max_bars=7):
    if df.empty:
        return []
    d = df.dropna(subset=["created_at"]).copy()
    if d.empty:
        return []
    d["day"] = pd.to_datetime(d["created_at"]).dt.date
    g = d.groupby("day")["price"].sum().fillna(0).sort_index().tail(max_bars)
    if g.empty:
        return []
    mx = g.max() or 1
    return [(day.strftime("%b %d"), int(val / mx * 100), float(val)) for day, val in g.items()]

def revenue_by_month(df, max_bars=12):
    if df.empty:
        return []
    d = df.dropna(subset=["created_at"]).copy()
    if d.empty:
        return []
    d["month"] = pd.to_datetime(d["created_at"]).dt.to_period("M")
    g = d.groupby("month")["price"].sum().fillna(0).sort_index().tail(max_bars)
    if g.empty:
        return []
    mx = g.max() or 1
    return [(str(p), int(val / mx * 100), float(val)) for p, val in g.items()]

def reservations_by_vehicle(df):
    if df.empty:
        return []
    g = df.groupby("vehicle").size().sort_values(ascending=False)
    return [(str(name), int(count)) for name, count in g.items()]


def operations_rows(df, limit=12):
    rows = []
    for _, r in df.head(limit).iterrows():
        dt = r["pickup_date"].strftime("%b %d %Y") if pd.notna(r["pickup_date"]) else "-"
        tm = r["pickup_time"].strftime("%I:%M %p") if pd.notna(r["pickup_time"]) else "-"
        status = (r["status"] or "").capitalize()
        rows.append((r["id"], r["dropoff_location"] or "-", dt, tm,
                     r["vehicle"], bool(r["child_seat_requested"]),
                     float(r["price"] or 0), status))
    return rows


# =========================================================================
# 5. HELPERS D'AFFICHAGE
# =========================================================================
def mi(name):
    return f'<span class="mi">{name}</span>'


def money(n):
    return "$" + format(int(round(n)), ",")

def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reservations")
    return output.getvalue()

def vbars_html(items):
    if not items:
        return '<p style="color:#8b8f98">Aucune donnée de revenu.</p>'
    cells = ""
    for lab, h, amount in items:
        cells += (f'<div class="vbar">'
                  f'<div class="vval">{money(amount)}</div>'
                  f'<div class="bar" style="height:{h}%"></div>'
                  f'<div class="lab">{lab}</div></div>')
    return f"""
    <div class="vbars">
      <div class="yaxis"><span>max</span><span></span><span></span><span></span><span>$0</span></div>
      {cells}
    </div>"""

def hbars_html(items):
    if not items:
        return '<p style="color:#8b8f98">Aucune réservation.</p>'
    mx = max(v for _, v in items) or 1
    rows = ""
    for name, val in items:
        w = val / mx * 100
        rows += (f'<div class="hbar"><span class="name">{name}</span>'
                 f'<div class="track"><div class="fill" style="width:{w:.0f}%"></div></div>'
                 f'<span class="v">{val}</span></div>')
    return rows


def table_html(ops):
    if not ops:
        return '<p style="color:#8b8f98">Aucune réservation à afficher.</p>'
    cls = {"Confirmed": "b-ok", "Pending": "b-wait", "Cancelled": "b-no"}
    body = ""
    for n, dest, dt, tm, veh, child, total, status in ops:
        badge_cls = cls.get(status, "b-wait")
        cs = '<span class="yes">Yes</span>' if child else '<span class="no">No</span>'
        body += (f'<tr><td class="muted">{n}</td><td class="dest">{dest}</td>'
                 f'<td class="muted">{dt}</td><td class="muted">{tm}</td><td>{veh}</td>'
                 f'<td>{cs}</td><td class="total">{money(total)}</td>'
                 f'<td><span class="badge {badge_cls}">{status}</span></td></tr>')
    return f"""
    <table class="ops">
      <thead><tr><th>#</th><th>Destination</th><th>Date</th><th>Time</th>
      <th>Vehicle</th><th>Child Seat</th><th>Total</th><th>Status</th></tr></thead>
      <tbody>{body}</tbody>
    </table>"""


# =========================================================================
# 6. PAGES
# =========================================================================
def render_dashboard(df):
    stats = compute_stats(df)
    st.markdown(f"""
      <div class="hero"><h1>SmartLimo Dashboard</h1>
      <p>{mi('location_on')} Orlando International · {date.today().strftime('%B %Y')}</p></div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
      <div class="stats">
        <div class="stat"><div class="top">Total Reservations<span class="ic">{mi('event')}</span></div><div class="val">{stats['total']}</div></div>
        <div class="stat"><div class="top">Total Revenue<span class="ic">{mi('payments')}</span></div><div class="val">{money(stats['revenue'])}</div></div>
        <div class="stat"><div class="top">Pending<span class="ic">{mi('schedule')}</span></div><div class="val">{stats['pending']}</div></div>
        <div class="stat"><div class="top">Confirmation Rate<span class="ic">{mi('check_circle')}</span></div><div class="val">{stats['conf']}%</div></div>
        <div class="stat"><div class="top">Child Seats Requested<span class="ic">{mi('child_care')}</span></div><div class="val">{stats['child']}</div></div>
      </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
      <div class="charts">
        <div class="card">
          <div class="head"><span class="t">Revenue by Day</span><span class="s">USD ($)</span></div>
          {vbars_html(revenue_by_day(df))}
        </div>
        <div class="card">
          <div class="head"><span class="t">Reservations by Vehicle</span><span class="s">Trip Count</span></div>
          {hbars_html(reservations_by_vehicle(df))}
        </div>
      </div>
    """, unsafe_allow_html=True)

    # ---------- LISTE + EXPORT ----------
    ops = operations_rows(df)
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown('<div class="list-title">Live Orlando Operations List</div>', unsafe_allow_html=True)
    with h2:
        cols = ["#", "Destination", "Date", "Time", "Vehicle", "Child Seat", "Total", "Status"]
        export_df = pd.DataFrame(
            [(n, d, dt, tm, v, "Yes" if c else "No", total, s)
             for n, d, dt, tm, v, c, total, s in ops], columns=cols)
        st.download_button(
            "Export Excel",
            icon=":material/download:",
            data=to_excel_bytes(export_df),
            file_name="reservations.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    st.markdown(table_html(ops), unsafe_allow_html=True)


def render_reservations(df):
    st.markdown(f"""
      <div class="hero"><h1>Reservations</h1>
      <p>{mi('event')} Toutes les réservations ({len(df)})</p></div>
    """, unsafe_allow_html=True)
    st.markdown(table_html(operations_rows(df, limit=100)), unsafe_allow_html=True)


def render_vehicles(df):
    st.markdown(f"""
      <div class="hero"><h1>Vehicles</h1>
      <p>{mi('directions_car')} Répartition des trajets par véhicule</p></div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
      <div class="card">
        <div class="head"><span class="t">Reservations by Vehicle</span><span class="s">Trip Count</span></div>
        {hbars_html(reservations_by_vehicle(df))}
      </div>
    """, unsafe_allow_html=True)


def render_reports(df):
    st.markdown(f"""
      <div class="hero"><h1>Reports</h1>
      <p>{mi('bar_chart')} Revenus par jour et par mois</p></div>
    """, unsafe_allow_html=True)

    # --- Revenu par jour ---
    st.markdown(f"""
      <div class="card">
        <div class="head"><span class="t">Revenue by Day</span><span class="s">USD ($)</span></div>
        {vbars_html(revenue_by_day(df))}
      </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- Revenu par mois ---
    st.markdown(f"""
      <div class="card">
        <div class="head"><span class="t">Revenue by Month</span><span class="s">USD ($)</span></div>
        {vbars_html(revenue_by_month(df))}
      </div>
    """, unsafe_allow_html=True)


# =========================================================================
# 7. APP
# =========================================================================
def nav_button(label, page_key):
    is_active = st.session_state["page"] == page_key
    if st.button(label, use_container_width=True,
                 type="primary" if is_active else "secondary",
                 key=f"nav_{page_key}"):
        st.session_state["page"] = page_key
        st.rerun()


def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "Dashboard"

    with st.sidebar:
        st.markdown(f"""
          <div class="s-brand"><div class="s-logo">{mi('directions_car')}</div>
          <div class="s-name">SmartLimo <span>AI</span></div></div>
        """, unsafe_allow_html=True)

        nav_button("Dashboard", "Dashboard")
        nav_button("Reservations", "Reservations")
        nav_button("Vehicles", "Vehicles")
        nav_button("Reports", "Reports")

        initials = "".join(w[0] for w in ADMIN_PROFILE["name"].split()[:2])
        st.markdown(f"""
          <div class="s-user"><div class="s-av">{initials}</div>
          <div><div class="s-uname">{ADMIN_PROFILE['name']}</div>
          <div class="s-urole">{ADMIN_PROFILE['role']}</div></div></div>
        """, unsafe_allow_html=True)

        if st.button("Logout", icon=":material/logout:", use_container_width=True, key="logout_btn"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    # --- Sécurité : si la base n'est pas joignable, on prévient au lieu de planter
    if not DB_OK:
        st.error("Impossible de se connecter au backend / à la base de données.")
        st.caption(f"Détail technique : {DB_ERROR}")
        st.info("Vérifie que le dossier backend est accessible et que DATABASE_URL "
                "est bien défini dans backend/.env.")
        return

    try:
        df = load_reservations()
    except Exception as e:
        st.error("Erreur lors de la lecture des réservations.")
        st.caption(f"Détail technique : {e}")
        return

    if df.empty:
        st.warning("Aucune réservation dans la base pour le moment. "
                   "Crée quelques réservations via le chatbot, puis recharge cette page.")

    page = st.session_state["page"]
    if page == "Dashboard":
        render_dashboard(df)
    elif page == "Reservations":
        render_reservations(df)
    elif page == "Vehicles":
        render_vehicles(df)
    elif page == "Reports":
        render_reports(df)


# =========================================================================
# 8. ENTRÉE
# =========================================================================
if login_gate():
    main()
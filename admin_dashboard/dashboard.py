import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="SmartLimo Admin", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    h1, h2, h3 { color: #2d3a4a !important; }
    div[data-testid="stMetric"] {
        background-color: #f5f5f7;
        border-radius: 16px;
        padding: 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3ec6c6 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("SmartLimo — Tableau de bord")

API_URL = "http://127.0.0.1:8000"
df = pd.DataFrame(requests.get(f"{API_URL}/reservations/").json())
df['created_at'] = pd.to_datetime(df['created_at'])
df['jour'] = df['created_at'].dt.date

tab1, tab2 = st.tabs(["Réservations", "Statistiques"])

with tab1:
    st.subheader("Toutes les réservations")
    if 'status' in df.columns:
        status_options = ["Tous"] + df['status'].unique().tolist()
        status_filter = st.selectbox("Filtrer par statut", status_options)
        df_filtered = df[df['status'] == status_filter] if status_filter != "Tous" else df
    else:
        df_filtered = df
    st.dataframe(df_filtered, use_container_width=True, height=400)
    st.download_button("Télécharger en CSV", df_filtered.to_csv(index=False), "reservations.csv")

with tab2:
    st.subheader("Vue d'ensemble")
    col1, col2, col3 = st.columns(3)
    col1.metric("Réservations totales", len(df))
    col2.metric("Revenu total", f"${df['price'].sum():.2f}" if 'price' in df.columns else "N/A")
    col3.metric("Confirmées", len(df[df['status'] == 'confirmed']) if 'status' in df.columns else 0)

    st.markdown("---")

    st.subheader("Consulter une date précise")
    selected_date = st.date_input("Choisir une date")
    day_data = df[df['jour'] == selected_date]

    colA, colB = st.columns(2)
    colA.metric("Réservations ce jour", len(day_data))
    colB.metric("Coût total ce jour", f"${day_data['price'].sum():.2f}" if len(day_data) > 0 else "$0.00")

    if len(day_data) > 0:
        st.dataframe(day_data, use_container_width=True)
    else:
        st.info("Aucune réservation ce jour-là.")

    st.markdown("---")

    if 'vehicle_id' in df.columns:
        st.subheader("Réservations par véhicule")
        counts = df['vehicle_id'].value_counts()
        fig = go.Figure(go.Bar(x=counts.index.astype(str), y=counts.values, marker_color="#3ec6c6"))
        fig.update_layout(paper_bgcolor="white", plot_bgcolor="white", font={'color': '#2d3a4a'}, height=300)
        st.plotly_chart(fig, use_container_width=True)
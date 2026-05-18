import streamlit as st
import pandas as pd


def render_kpi_cards(df: pd.DataFrame) -> None:
    """Renderiza os 4 cards de KPI (distância, tempo, velocidade, altimetria)."""
    dist_total  = round(df["distance_km"].sum(), 2)
    tempo_total = (round(df["moving_time_min"].sum(), 2))/60
    vel_media   = round(df["speed_kmh"].mean(), 2)
    alt_total   = round(df["total_elevation_gain"].sum(), 2)

    kpis = [
        ("🚴", "Distância Total",  f"{dist_total} km"),
        ("🕒", "Tempo Total",      f"{tempo_total:.1f} h"),
        ("⚡", "Velocidade Média", f"{vel_media} km/h"),
        ("⛰️", "Altimetria",       f"{alt_total} m"),
    ]

    for col, (icon, title, value) in zip(st.columns(4), kpis):
        with col:
            st.markdown(f'''
            <div class="card">
                <div class="card-icon">{icon}</div>
                <div class="card-title">{title}</div>
                <div class="card-value">{value}</div>
            </div>
            ''', unsafe_allow_html=True)


def render_pr_cards(df: pd.DataFrame) -> None:
    """Renderiza os 4 cards de recordes pessoais (PRs)."""
    pr_dist  = df["distance_km"].max()
    pr_vel   = df["speed_kmh"].max()
    pr_alt   = df["total_elevation_gain"].max()
    pr_tempo = df["moving_time_min"].max() / 60

    prs = [
        ("🏆", "PR Distância",  f"{pr_dist:.1f} km"),
        ("⚡", "PR Velocidade", f"{pr_vel:.1f} km/h"),
        ("⛰️", "KOM Subida",    f"{pr_alt:.0f} m"),
        ("🚴", "Longão",        f"{pr_tempo:.1f} h"),
    ]

    for col, (icon, title, value) in zip(st.columns(4), prs):
        with col:
            st.markdown(f'''
            <div class="pr-card">
                <div class="pr-icon">{icon}</div>
                <div class="pr-title">{title}</div>
                <div class="pr-value">{value}</div>
            </div>
            ''', unsafe_allow_html=True)

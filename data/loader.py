import pandas as pd
import streamlit as st
from strava_client import get_activities


@st.cache_data(ttl=600)
def load_activities() -> list[dict]:
    """Busca atividades da Strava e cacheia por 10 minutos."""
    return get_activities()


def build_dataframe() -> pd.DataFrame:
    """
    Carrega as atividades, filtra apenas pedais (Ride) e
    adiciona as colunas calculadas usadas em todo o dashboard.
    """
    data = load_activities()
    df   = pd.DataFrame(data)

    df = df[df["type"] == "Ride"].copy()
    df["start_date"]      = pd.to_datetime(df["start_date"]).dt.tz_localize(None)
    df["distance_km"]     = df["distance"] / 1000
    df["moving_time_min"] = df["moving_time"] / 60
    df["speed_kmh"]       = df["average_speed"] * 3.6

    return df


def apply_period_filter(df: pd.DataFrame, periodo: str, dias_custom: int = 30) -> pd.DataFrame:
    """
    Filtra o DataFrame pelo período selecionado na sidebar.
    Recebe o label do selectbox e, se for 'Personalizado', usa dias_custom.
    """
    if periodo == "Tudo":
        return df

    if periodo == "Personalizado":
        dias = dias_custom
    else:
        dias = int(periodo.split()[0])

    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias)
    return df[df["start_date"] >= data_limite]

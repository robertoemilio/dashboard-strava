import requests
import streamlit as st
 
 
# =========================
# CONFIGURAÇÃO
# =========================
 
_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_API_BASE  = "https://www.strava.com/api/v3"
 
 
# =========================
# AUTENTICAÇÃO (token único por sessão)
# =========================
 
@st.cache_data(ttl=3600)
def _get_access_token() -> str:
    """
    Obtém e cacheia o access token da Strava por até 1 hora.
    Evita múltiplas chamadas de refresh em um mesmo carregamento de página.
    """
    payload = {
        "client_id":     st.secrets["STRAVA_CLIENT_ID"],
        "client_secret": st.secrets["STRAVA_CLIENT_SECRET"],
        "refresh_token": st.secrets["STRAVA_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    }
    res = requests.post(_STRAVA_TOKEN_URL, data=payload, timeout=10)
    res.raise_for_status()
    return res.json()["access_token"]
 
 
def _auth_headers() -> dict:
    """Retorna o header de autenticação pronto para uso."""
    return {"Authorization": f"Bearer {_get_access_token()}"}
 
 
# =========================
# FUNÇÕES PÚBLICAS DA API
# =========================
 
def get_activities() -> list[dict]:
    """Busca todas as atividades do atleta, paginando automaticamente."""
    url      = f"{_STRAVA_API_BASE}/athlete/activities"
    headers  = _auth_headers()
    all_data = []
    page     = 1
 
    while True:
        res = requests.get(url, headers=headers,
                           params={"per_page": 50, "page": page}, timeout=10)
        res.raise_for_status()
        batch = res.json()
        if not batch:
            break
        all_data.extend(batch)
        page += 1
 
    return all_data
 
 
def get_activity_streams(activity_id: int) -> dict:
    """Retorna os streams de uma atividade (distância, velocidade, altitude, tempo)."""
    res = requests.get(
        f"{_STRAVA_API_BASE}/activities/{activity_id}/streams",
        headers=_auth_headers(),
        params={"keys": "distance,velocity_smooth,altitude,time", "key_by_type": "true"},
        timeout=10,
    )
    res.raise_for_status()
    return res.json()
 
 
def get_activity_map(activity_id: int) -> str | None:
    """Retorna o summary_polyline de uma atividade, ou None se indisponível."""
    res = requests.get(f"{_STRAVA_API_BASE}/activities/{activity_id}",
                       headers=_auth_headers(), timeout=10)
    res.raise_for_status()
    return res.json().get("map", {}).get("summary_polyline")
 
 
def get_activity_segments(activity_id: int) -> list[dict]:
    """
    Retorna os segment_efforts de uma atividade específica.
    Cada item contém nome, id do segmento, tempo e data do esforço.
    """
    res = requests.get(
        f"{_STRAVA_API_BASE}/activities/{activity_id}",
        headers=_auth_headers(),
        timeout=10,
    )
    res.raise_for_status()
    efforts = res.json().get("segment_efforts", [])
 
    return [
        {
            "segment_id":   e["segment"]["id"],
            "name":         e["segment"]["name"],
            "elapsed_time": e["elapsed_time"],
            "distance_m":   e["segment"]["distance"],
            "date":         e["start_date_local"],
        }
        for e in efforts
    ]
 
 
@st.cache_data(ttl=600)
def get_segment_efforts(segment_id: int) -> list[dict]:
    """
    Retorna todas as passagens do atleta por um segmento específico,
    ordenadas da mais antiga para a mais recente.
    Cacheado por 10 minutos para evitar chamadas repetidas ao trocar de segmento.
    """
    all_efforts = []
    page        = 1
 
    while True:
        res = requests.get(
            f"{_STRAVA_API_BASE}/segments/{segment_id}/all_efforts",
            headers=_auth_headers(),
            params={"per_page": 50, "page": page},
            timeout=10,
        )
        res.raise_for_status()
        batch = res.json()
        if not batch:
            break
        all_efforts.extend(batch)
        page += 1
 
    return sorted(all_efforts, key=lambda e: e["start_date_local"])
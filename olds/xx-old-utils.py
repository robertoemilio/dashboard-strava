import pandas as pd
import streamlit as st
from strava_client import get_activities


# =========================
# CARREGAMENTO DE DADOS
# =========================

@st.cache_data(ttl=600)
def load_activities() -> list[dict]:
    
    # Busca as atividades da Strava e cacheia por 10 minutos.
    # O cache era feito no app.py — centralizado aqui para não depender
    # de quem chama a função.
    
    return get_activities()


# =========================
# ANÁLISE SEMANAL
# =========================

def _calcular_variacao(dist_ultima: float, dist_anterior: float) -> float:
    # Calcula a variação percentual de volume entre duas semanas.
    if dist_anterior <= 0:
        return 0.0
    return ((dist_ultima - dist_anterior) / dist_anterior) * 100


def gerar_analise(df: pd.DataFrame) -> str:
    
    # Compara o volume da última semana com a semana anterior e
    # retorna uma mensagem de análise com recomendação.
    
    if df.empty:
        return "Sem dados suficientes para análise."

    data_max = df["start_date"].max()

    ultima_semana = df[df["start_date"] >= data_max - pd.Timedelta(days=7)]
    semana_anterior = df[
        (df["start_date"] >= data_max - pd.Timedelta(days=14)) &
        (df["start_date"] <  data_max - pd.Timedelta(days=7))
    ]

    dist_ultima   = ultima_semana["distance_km"].sum()
    dist_anterior = semana_anterior["distance_km"].sum()
    dias_ativos   = ultima_semana["start_date"].dt.date.nunique()
    variacao      = _calcular_variacao(dist_ultima, dist_anterior)

    linhas = ["🧠 **Análise Inteligente**\n"]

    # Evolução de volume
    if variacao > 10:
        linhas.append(f"📈 Você aumentou {variacao:.1f}% seu volume semanal.")
    elif variacao < -10:
        linhas.append(f"📉 Seu volume caiu {abs(variacao):.1f}%.")
    else:
        linhas.append("📊 Seu volume está estável.")

    # Frequência
    linhas.append(f"🚴 Você pedalou {dias_ativos} dia(s) na última semana.")

    # Alerta de overtraining
    if variacao > 30:
        linhas.append("⚠️ Risco de overtraining! Considere reduzir a intensidade.")

    # Recomendação
    linhas.append("\n💡 **Recomendação:**")
    if variacao > 20:
        linhas.append("Faça treinos leves ou descanso ativo nos próximos dias.")
    elif variacao < -20:
        linhas.append("Você pode aumentar o volume gradualmente.")
    else:
        linhas.append("Mantenha consistência — você está no caminho certo.")

    # Meta sugerida (+/- 10% do volume atual)
    meta_min = dist_ultima * 0.9
    meta_max = dist_ultima * 1.1
    linhas.append(f"\n🎯 Meta sugerida: entre {meta_min:.1f} km e {meta_max:.1f} km na próxima semana.")

    return "\n".join(linhas)


# =========================
# ANÁLISE DE ATIVIDADE INDIVIDUAL
# =========================

def _segmentar_velocidade(velocidade_kmh: list[float]) -> tuple[list, list, list]:
    # Divide a lista de velocidades em início, meio e fim (terços iguais).
    n = len(velocidade_kmh)
    return (
        velocidade_kmh[: n // 3],
        velocidade_kmh[n // 3 : 2 * n // 3],
        velocidade_kmh[2 * n // 3 :],
    )


def _detectar_queda(
    velocidade_kmh: list[float],
    distancia: list[float],
    media_inicio: float,
) -> float | None:
    
    # Retorna o km onde a velocidade caiu abaixo de 80% da média inicial,
    # ou None se não houver queda significativa.
    
    for i, v in enumerate(velocidade_kmh):
        if v < media_inicio * 0.8:
            return distancia[i] / 1000
    return None


def analisar_atividade(streams: dict) -> str:
    
    # Analisa os streams de velocidade de uma atividade e retorna
    # um texto com diagnóstico de ritmo e fadiga.
    
    velocidade_kmh = [v * 3.6 for v in streams["velocity_smooth"]["data"]]
    distancia      = streams["distance"]["data"]
    n              = len(velocidade_kmh)

    inicio, meio, fim = _segmentar_velocidade(velocidade_kmh)

    media_inicio = sum(inicio) / len(inicio)
    media_meio   = sum(meio)   / len(meio)
    media_fim    = sum(fim)    / len(fim)
    media_geral  = sum(velocidade_kmh) / n

    linhas = [
        "🚴 **Análise da atividade**\n",
        f"Velocidade média geral: {media_geral:.1f} km/h\n",
        f"📊 Início: {media_inicio:.1f} km/h",
        f"📊 Meio:   {media_meio:.1f} km/h",
        f"📊 Final:  {media_fim:.1f} km/h\n",
    ]

    # Queda progressiva
    if media_fim < media_inicio * 0.85:
        km_queda = _detectar_queda(velocidade_kmh, distancia, media_inicio)
        if km_queda is not None:
            linhas.append(f"📉 Queda de performance por volta de {km_queda:.1f} km")
    else:
        linhas.append("💪 Ritmo consistente durante o treino")

    # Insights de fadiga e pacing
    if media_meio > media_fim:
        linhas.append("\n⚠️ Indício de fadiga progressiva no final do treino")

    if media_inicio > media_meio:
        linhas.append("⚠️ Você pode ter começado forte demais")

    return "\n".join(linhas)

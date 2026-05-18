import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures


# =========================
# ANÁLISE SEMANAL
# =========================

def calcular_volume_semanal(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa as atividades por semana e retorna o volume em km por semana."""
    df = df.copy()
    df["week"] = df["start_date"].dt.to_period("W").apply(lambda r: r.start_time)
    return df.groupby("week")["distance_km"].sum().reset_index().sort_values("week")


def prever_proxima_semana(df_week: pd.DataFrame) -> tuple[float, pd.DataFrame] | tuple[None, pd.DataFrame]:
    """
    Ajusta um modelo de regressão polinomial (grau 2) ao volume semanal
    e retorna (previsão_km, df_week com colunas 'trend' e 'tipo').
    Retorna (None, df_week) se não houver dados suficientes (< 4 semanas).
    """
    if len(df_week) < 4:
        df_week["tipo"] = "Real"
        return None, df_week

    df_week = df_week.copy()
    df_week["t"] = np.arange(len(df_week))

    poly   = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(df_week[["t"]])
    model  = LinearRegression().fit(X_poly, df_week["distance_km"])

    next_t   = np.array([[df_week["t"].max() + 1]])
    previsao = model.predict(poly.transform(next_t))[0]

    df_week["trend"] = model.predict(X_poly)
    df_week["tipo"]  = "Real"

    return previsao, df_week


def gerar_analise(df: pd.DataFrame) -> str:
    """
    Compara o volume da última semana com a semana anterior e
    retorna uma mensagem de análise com recomendação.
    """
    if df.empty:
        return "Sem dados suficientes para análise."

    data_max = df["start_date"].max()

    ultima_semana  = df[df["start_date"] >= data_max - pd.Timedelta(days=7)]
    semana_anterior = df[
        (df["start_date"] >= data_max - pd.Timedelta(days=14)) &
        (df["start_date"] <  data_max - pd.Timedelta(days=7))
    ]

    dist_ultima   = ultima_semana["distance_km"].sum()
    dist_anterior = semana_anterior["distance_km"].sum()
    dias_ativos   = ultima_semana["start_date"].dt.date.nunique()

    variacao = ((dist_ultima - dist_anterior) / dist_anterior * 100) if dist_anterior > 0 else 0.0

    linhas = ["🧠 **Análise Inteligente**\n"]

    if variacao > 10:
        linhas.append(f"📈 Você aumentou {variacao:.1f}% seu volume semanal.")
    elif variacao < -10:
        linhas.append(f"📉 Seu volume caiu {abs(variacao):.1f}%.")
    else:
        linhas.append("📊 Seu volume está estável.")

    linhas.append(f"🚴 Você pedalou {dias_ativos} dia(s) na última semana.")

    if variacao > 30:
        linhas.append("⚠️ Risco de overtraining! Considere reduzir a intensidade.")

    linhas.append("\n💡 **Recomendação:**")
    if variacao > 20:
        linhas.append("Faça treinos leves ou descanso ativo nos próximos dias.")
    elif variacao < -20:
        linhas.append("Você pode aumentar o volume gradualmente.")
    else:
        linhas.append("Mantenha consistência — você está no caminho certo.")

    meta_min = dist_ultima * 0.9
    meta_max = dist_ultima * 1.1
    linhas.append(f"\n🎯 Meta sugerida: entre {meta_min:.1f} km e {meta_max:.1f} km na próxima semana.")

    return "\n".join(linhas)


def calcular_meta(df_week: pd.DataFrame, previsao: float) -> dict:
    """
    Calcula meta semanal, mensal, ajustada e classificação de risco.
    Retorna um dicionário com os valores prontos para exibição.
    """
    ultimas_4     = df_week.tail(4)["distance_km"].values
    ultima_semana = ultimas_4[-1]
    meta_final    = (ultima_semana * 1.10 + previsao) / 2
    meta_mensal   = meta_final * 4.3
    aumento_pct   = ((meta_final - ultima_semana) / ultima_semana * 100) if ultima_semana else 0

    media  = np.mean(ultimas_4[:-1])
    desvio = np.std(ultimas_4)
    variacao_recente = ((ultima_semana - media) / media * 100) if media != 0 else 0

    if desvio < 10:
        fator, consistencia = 1.10, "alta"
    elif desvio < 25:
        fator, consistencia = 1.05, "moderada"
    else:
        fator, consistencia = 0.95, "baixa"

    return {
        "meta_final":       meta_final,
        "meta_mensal":      meta_mensal,
        "meta_ajustada":    meta_final * fator,
        "aumento_pct":      aumento_pct,
        "variacao_recente": variacao_recente,
        "consistencia":     consistencia,
        "ultima_semana":    ultima_semana,
    }


# =========================
# ANÁLISE DE ATIVIDADE INDIVIDUAL
# =========================

def analisar_atividade(streams: dict) -> str:
    """Analisa ritmo e fadiga de uma atividade a partir dos streams de velocidade."""
    velocidade_kmh = [v * 3.6 for v in streams["velocity_smooth"]["data"]]
    distancia      = streams["distance"]["data"]
    n              = len(velocidade_kmh)

    terco          = n // 3
    inicio         = velocidade_kmh[:terco]
    meio           = velocidade_kmh[terco: 2 * terco]
    fim            = velocidade_kmh[2 * terco:]

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

    if media_fim < media_inicio * 0.85:
        km_queda = next(
            (distancia[i] / 1000 for i, v in enumerate(velocidade_kmh) if v < media_inicio * 0.8),
            None,
        )
        if km_queda:
            linhas.append(f"📉 Queda de performance por volta de {km_queda:.1f} km")
    else:
        linhas.append("💪 Ritmo consistente durante o treino")

    if media_meio > media_fim:
        linhas.append("\n⚠️ Indício de fadiga progressiva no final do treino")
    if media_inicio > media_meio:
        linhas.append("⚠️ Você pode ter começado forte demais")

    return "\n".join(linhas)


def detectar_zonas_fadiga(streams: dict) -> dict:
    """
    Detecta os pontos de fadiga e quebra de ritmo na atividade.
    Retorna um dicionário com velocidade_kmh, dist_km, fadiga_index,
    quebra_index e pacing_ideal.
    """
    velocidade_kmh = [v * 3.6 for v in streams["velocity_smooth"]["data"]]
    dist_km        = [d / 1000 for d in streams["distance"]["data"]]
    n              = len(velocidade_kmh)

    inicio_idx = int(n * 0.25)
    ritmo_base = sum(velocidade_kmh[:inicio_idx]) / inicio_idx

    fadiga_index = None
    quebra_index = None

    for i in range(inicio_idx, n - 15):
        trecho = velocidade_kmh[i: i + 15]
        if fadiga_index is None and all(v < ritmo_base * 0.85 for v in trecho):
            fadiga_index = i
        if all(v < ritmo_base * 0.50 for v in trecho):
            quebra_index = i
            break

    trecho_bom      = velocidade_kmh[:fadiga_index] if fadiga_index else velocidade_kmh[:int(n * 0.3)]
    trecho_filtrado = [v for v in trecho_bom if 8 < v < 25]
    limite_superior = np.percentile(trecho_filtrado, 90)
    trecho_filtrado = [v for v in trecho_filtrado if v <= limite_superior]
    pacing_ideal    = float(np.median(trecho_filtrado))

    return {
        "velocidade_kmh": velocidade_kmh,
        "dist_km":        dist_km,
        "fadiga_index":   fadiga_index,
        "quebra_index":   quebra_index,
        "pacing_ideal":   pacing_ideal,
        "media_geral":    sum(velocidade_kmh) / n,
    }


# =========================
# ANÁLISE DE EVOLUÇÃO POR SEGMENTO
# =========================

def analisar_evolucao_segmento(efforts: list[dict]) -> pd.DataFrame:
    """
    Recebe a lista de esforços de um segmento (retornada por get_segment_efforts)
    e retorna um DataFrame pronto para plotar, com colunas:
      - data         : datetime da passagem
      - tempo_s      : tempo em segundos
      - tempo_str    : tempo formatado (mm:ss)
      - velocidade   : velocidade média em km/h
      - is_pr        : bool, True na passagem mais rápida
      - variacao_pct : variação percentual em relação ao esforço anterior
      - tendencia    : valores suavizados por média móvel (3 esforços)
    """
    if not efforts:
        return pd.DataFrame()

    df = pd.DataFrame([
        {
            "data":       pd.to_datetime(e["start_date_local"]),
            "tempo_s":    e["elapsed_time"],
            "distancia_m": e["distance"],
        }
        for e in efforts
    ]).sort_values("data").reset_index(drop=True)

    # Tempo formatado mm:ss
    df["tempo_str"] = df["tempo_s"].apply(
        lambda s: f"{int(s) // 60}:{int(s) % 60:02d}"
    )

    # Velocidade média km/h
    df["velocidade"] = (df["distancia_m"] / df["tempo_s"] * 3.6).round(1)

    # PR = menor tempo
    df["is_pr"] = df["tempo_s"] == df["tempo_s"].min()

    # Variação % em relação ao esforço anterior (tempo menor = melhora = negativo)
    df["variacao_pct"] = df["tempo_s"].pct_change() * 100

    # Tendência suavizada (média móvel de 3)
    df["tendencia"] = df["tempo_s"].rolling(window=3, min_periods=1).mean()

    return df
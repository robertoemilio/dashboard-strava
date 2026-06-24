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
# ANÁLISE DE ZONAS DE TREINO
# =========================

ZONAS = [
    {"zona": "Z1", "nome": "Recuperação",  "cor": "#4fc3f7"},
    {"zona": "Z2", "nome": "Endurance",    "cor": "#81c784"},
    {"zona": "Z3", "nome": "Tempo",        "cor": "#fff176"},
    {"zona": "Z4", "nome": "Limiar",       "cor": "#ffb74d"},
    {"zona": "Z5", "nome": "VO2 Max",      "cor": "#e57373"},
]

# Limites inferiores de cada zona (índice 0=Z1 ... 4=Z5)
# FC: % da FC máxima | Potência: % do FTP
_FC_LIMITES  = [0, 0.60, 0.70, 0.80, 0.90]
_POT_LIMITES = [0, 0.55, 0.75, 0.90, 1.05]


def _classificar_zona(valor: float, limites: list[float]) -> int:
    """Retorna o índice da zona (0-4) dado um valor normalizado (% do máximo)."""
    for i in range(4, 0, -1):
        if valor >= limites[i]:
            return i
    return 0


def calcular_zonas(
    streams: dict,
    fc_max: int,
    ftp: int,
) -> dict:
    """
    Calcula o tempo e percentual em cada zona Z1-Z5 para uma atividade.

    Parâmetros
    ----------
    streams : dict   — streams retornados por get_activity_streams()
    fc_max  : int    — FC máxima do atleta em bpm  (ex: 185)
    ftp     : int    — FTP do atleta em watts       (ex: 200)

    Retorna
    -------
    dict com chaves 'fc' e 'potencia', cada uma contendo um DataFrame
    com colunas: zona, nome, cor, tempo_s, tempo_str, percentual.
    Retorna None em cada chave se o stream correspondente não existir.
    """
    time_data = streams.get("time", {}).get("data", [])
    resultado = {}

    for metrica, chave_stream, limites, referencia in [
        ("fc",       "heartrate", _FC_LIMITES,  fc_max),
        ("potencia", "watts",     _POT_LIMITES, ftp),
    ]:
        stream = streams.get(chave_stream, {}).get("data")

        if not stream or not time_data:
            resultado[metrica] = None
            continue

        # Tempo em cada zona (segundos)
        tempo_zonas = [0] * 5

        for i in range(1, min(len(stream), len(time_data))):
            dt    = time_data[i] - time_data[i - 1]
            valor = stream[i] / referencia
            zona  = _classificar_zona(valor, limites)
            tempo_zonas[zona] += dt

        total = sum(tempo_zonas) or 1

        rows = []
        for i, z in enumerate(ZONAS):
            t = tempo_zonas[i]
            rows.append({
                **z,
                "tempo_s":    t,
                "tempo_str":  f"{t // 60}min {t % 60:02d}s",
                "percentual": round(t / total * 100, 1),
            })

        resultado[metrica] = pd.DataFrame(rows)

    return resultado

# Limites de velocidade por zona (% da vel. máxima histórica)
_VEL_LIMITES = [0, 0.55, 0.68, 0.80, 0.90]


def calcular_zonas_velocidade(streams: dict, vel_max_kmh: float) -> pd.DataFrame:
    """
    Calcula tempo e percentual em cada zona Z1-Z5 usando velocidade
    como proxy de intensidade, baseado na velocidade máxima histórica.

    Parâmetros
    ----------
    streams      : dict  — streams de get_activity_streams()
    vel_max_kmh  : float — velocidade máxima histórica do atleta em km/h

    Retorna
    -------
    DataFrame com colunas: zona, nome, cor, tempo_s, tempo_str, percentual.
    """
    vel_data  = streams.get("velocity_smooth", {}).get("data", [])
    time_data = streams.get("time", {}).get("data", [])

    if not vel_data or not time_data:
        return pd.DataFrame()

    tempo_zonas = [0] * 5

    for i in range(1, min(len(vel_data), len(time_data))):
        dt    = time_data[i] - time_data[i - 1]
        # converte m/s → km/h e normaliza pela vel. máxima
        vel_kmh = vel_data[i] * 3.6
        valor   = vel_kmh / vel_max_kmh if vel_max_kmh > 0 else 0
        zona    = _classificar_zona(valor, _VEL_LIMITES)
        tempo_zonas[zona] += dt

    total = sum(tempo_zonas) or 1

    rows = []
    for i, z in enumerate(ZONAS):
        t = tempo_zonas[i]
        rows.append({
            **z,
            "tempo_s":    t,
            "tempo_str":  f"{t // 60}min {t % 60:02d}s",
            "percentual": round(t / total * 100, 1),
        })

    return pd.DataFrame(rows)


def estimar_ftp_velocidade(df: pd.DataFrame, all_streams_fn) -> float | None:
    """
    Estima o FTP em km/h buscando a melhor velocidade média sustentada
    por 20 minutos contínuos entre as últimas 90 dias de atividades.
    Aplica fator 0.95 sobre esse valor (protocolo padrão de teste de 20min).

    Parâmetros
    ----------
    df             : DataFrame de atividades já processado
    all_streams_fn : callable — função get_activity_streams(id)

    Retorna
    -------
    FTP estimado em km/h, ou None se não houver dados suficientes.
    """
    JANELA_S = 20 * 60   # 20 minutos em segundos

    df_recente = df.sort_values("start_date", ascending=False).head(20)
    melhor     = 0.0

    for _, row in df_recente.iterrows():
        try:
            streams  = all_streams_fn(int(row["id"]))
            vel_data = streams.get("velocity_smooth", {}).get("data", [])
            t_data   = streams.get("time", {}).get("data", [])

            if not vel_data or not t_data:
                continue

            # Janela deslizante de 20 minutos
            i_start = 0
            for i_end in range(len(t_data)):
                while t_data[i_end] - t_data[i_start] > JANELA_S:
                    i_start += 1
                trecho = vel_data[i_start:i_end + 1]
                if trecho:
                    media = sum(trecho) / len(trecho) * 3.6   # m/s → km/h
                    if media > melhor:
                        melhor = media

        except Exception:
            continue

    return round(melhor * 0.95, 1) if melhor > 0 else None


def calcular_zonas_ftp_estimado(streams: dict, ftp_kmh: float) -> pd.DataFrame:
    """
    Calcula zonas Z1–Z5 usando o FTP estimado em km/h como referência,
    seguindo os mesmos percentuais do padrão Coggan para potência.

    Parâmetros
    ----------
    streams  : dict  — streams de get_activity_streams()
    ftp_kmh  : float — FTP estimado em km/h (de estimar_ftp_velocidade)

    Retorna
    -------
    DataFrame com colunas: zona, nome, cor, tempo_s, tempo_str, percentual.
    """
    vel_data  = streams.get("velocity_smooth", {}).get("data", [])
    time_data = streams.get("time", {}).get("data", [])

    if not vel_data or not time_data or ftp_kmh <= 0:
        return pd.DataFrame()

    tempo_zonas = [0] * 5

    for i in range(1, min(len(vel_data), len(time_data))):
        dt      = time_data[i] - time_data[i - 1]
        vel_kmh = vel_data[i] * 3.6
        valor   = vel_kmh / ftp_kmh
        zona    = _classificar_zona(valor, _POT_LIMITES)
        tempo_zonas[zona] += dt

    total = sum(tempo_zonas) or 1

    rows = []
    for i, z in enumerate(ZONAS):
        t = tempo_zonas[i]
        rows.append({
            **z,
            "tempo_s":    t,
            "tempo_str":  f"{t // 60}min {t % 60:02d}s",
            "percentual": round(t / total * 100, 1),
        })

    return pd.DataFrame(rows)

import streamlit as st
import pandas as pd

# ── Configuração (deve ser a primeira chamada Streamlit) ──────────────────────
st.set_page_config(page_title="Dashboard Ciclismo", layout="wide")

# ── Módulos internos ──────────────────────────────────────────────────────────
from data.loader import build_dataframe, apply_period_filter
from strava_client import get_activity_streams, get_activity_map
from analysis.metrics import (
    calcular_volume_semanal,
    prever_proxima_semana,
    gerar_analise,
    calcular_meta,
    analisar_atividade,
    detectar_zonas_fadiga,
    calcular_zonas,
    calcular_zonas_velocidade,
    estimar_ftp_velocidade,
    calcular_zonas_ftp_estimado,
)
from ui.theme import load_css
from ui.kpi_cards import render_kpi_cards, render_pr_cards
from ui.charts import (
    render_evolucao,
    render_volume_semanal,
    render_graficos_por_pedal,
    render_plano_semanal,
    render_velocidade_fadiga,
    render_zonas_treino,
    render_zonas_velocidade,
    render_zonas_ftp_estimado,
)
from ui.map_view import render_mapa


# ── Estilo ────────────────────────────────────────────────────────────────────
load_css()


# ── Dados ─────────────────────────────────────────────────────────────────────
if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()

df = build_dataframe()


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("📅 Filtro de Período")

periodo = st.sidebar.selectbox(
    "Selecione o período",
    ["Tudo", "7 dias", "30 dias", "90 dias", "180 dias", "365 dias", "Personalizado"],
)

dias_custom = 30
if periodo == "Personalizado":
    dias_custom = st.sidebar.number_input("Quantidade de dias", min_value=1, max_value=2000, value=30)

df = apply_period_filter(df, periodo, dias_custom)

if periodo == "Tudo":
    st.sidebar.info("📊 Exibindo todos os dados disponíveis")
else:
    dias = dias_custom if periodo == "Personalizado" else int(periodo.split()[0])
    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias)
    st.sidebar.info(f"📊 Exibindo dados desde {data_limite.date()}")

st.sidebar.divider()
st.sidebar.header("🫀 Zonas de Treino")
st.sidebar.caption("Usados para calcular Z1–Z5 na análise de cada atividade.")

idade  = st.sidebar.number_input("Sua idade (anos)", min_value=10, max_value=90, value=35)
fc_max = st.sidebar.number_input("FC máxima (bpm)",  min_value=100, max_value=250,
                                  value=220 - idade)
ftp    = st.sidebar.number_input("FTP (watts)",       min_value=50,  max_value=600, value=200)


# ── Título ────────────────────────────────────────────────────────────────────
st.title("🚴‍♂️ Dashboard de Ciclismo - Strava")


# ── Seção 1: KPIs ─────────────────────────────────────────────────────────────
st.subheader("📊 Resumo do período")
render_kpi_cards(df)


# ── Seção 2: Recordes Pessoais ────────────────────────────────────────────────
st.subheader("🏆 Recordes pessoais")
render_pr_cards(df)


# ── Seção 3: Evolução de distância ────────────────────────────────────────────
st.subheader("📈 Evolução de distância ao longo do tempo")
render_evolucao(df)


# ── Seção 4: Volume semanal + ML ──────────────────────────────────────────────
st.subheader("📅 Volume semanal + previsão (Machine Learning)")

df_week          = calcular_volume_semanal(df)
previsao, df_week = prever_proxima_semana(df_week)

if previsao is not None:
    proxima_semana = df_week["week"].max() + pd.Timedelta(days=7)
    df_previsao = pd.DataFrame({
        "week": [proxima_semana], "distance_km": [previsao], "tipo": ["Previsão"]
    })
    df_plot = pd.concat([df_week, df_previsao]).tail(20)
else:
    df_plot = df_week.tail(20)

render_volume_semanal(df_plot, df_week)


# ── Seção 5: Insights semanais ────────────────────────────────────────────────
st.subheader("🧠 Comparação e tendência semanal")

col_esq, col_dir = st.columns(2)

with col_esq:
    if len(df_week) >= 2:
        ultima   = df_week.iloc[-1]["distance_km"]
        anterior = df_week.iloc[-2]["distance_km"]
        variacao = ((ultima - anterior) / anterior * 100) if anterior != 0 else 0
        if variacao > 0:
            st.success(f"📈 {variacao:.1f}% a mais que a semana passada")
        elif variacao < 0:
            st.warning(f"📉 {abs(variacao):.1f}% a menos que a semana passada")
        else:
            st.info("➡️ Mesmo volume que a semana passada")

with col_dir:
    if len(df_week) >= 4:
        ultimas = df_week.tail(4)["distance_km"].values
        score   = sum(
            1 if ultimas[i] > ultimas[i - 1] else -1 if ultimas[i] < ultimas[i - 1] else 0
            for i in range(1, len(ultimas))
        )
        if score >= 2:
            st.success("🔥 Tendência de evolução nas últimas 4 semanas")
        elif score <= -2:
            st.error("⚠️ Tendência de queda nas últimas 4 semanas")
        else:
            st.info("➡️ Tendência estável nas últimas 4 semanas")


# ── Seção 6: Metas e plano semanal ───────────────────────────────────────────
if previsao is not None and len(df_week) >= 4:
    st.subheader("🎯 Metas e plano semanal")

    meta = calcular_meta(df_week, previsao)

    col1, col2, col3 = st.columns(3)
    with col1:
        diff  = meta["meta_final"] - meta["ultima_semana"]
        label = f"📈 +{diff:.2f} km" if diff > 0 else f"📉 {abs(diff):.2f} km"
        st.success(f"🎯 Meta semanal: {meta['meta_final']:.2f} km")
        st.info(label)
    with col2:
        st.success(f"📅 Meta mensal: {meta['meta_mensal']:.2f} km")
    with col3:
        if meta["aumento_pct"] <= 5:
            st.info("🟢 Meta leve (segura)")
        elif meta["aumento_pct"] <= 15:
            st.warning("🟡 Meta moderada (desafiadora)")
        else:
            st.error("🔴 Meta agressiva")

    st.subheader("📅 Plano semanal automático")
    render_plano_semanal(meta["meta_final"])

    st.subheader("🧠 Análise avançada de treino")
    col1, col2, col3 = st.columns(3)
    with col1:
        vr = meta["variacao_recente"]
        if vr > 30:
            st.error("🚨 Possível overtraining")
        elif vr > 15:
            st.warning("⚠️ Volume alto recente")
        else:
            st.success("✅ Volume controlado")
    with col2:
        if vr > 40:
            st.error("🛑 Alto risco de lesão")
        elif vr > 25:
            st.warning("⚠️ Risco moderado de lesão")
        else:
            st.info("🟢 Risco baixo de lesão")
    with col3:
        c = meta["consistencia"]
        if c == "alta":
            st.success("Alta consistência")
        elif c == "moderada":
            st.info("Consistência moderada")
        else:
            st.warning("Baixa consistência")

    st.success(f"⚙️ Meta ajustada pela consistência: {meta['meta_ajustada']:.2f} km")


# ── Seção 7: Análise inteligente ─────────────────────────────────────────────
st.subheader("🧠 Análise inteligente dos treinos")
st.info(gerar_analise(df))


# ── Seção 8: Gráficos por pedal ──────────────────────────────────────────────
st.subheader("🚴‍♂️ Análise por pedal")
render_graficos_por_pedal(df)


# ── Seção 9: Tabela de atividades ────────────────────────────────────────────
st.subheader("📋 Últimos pedais")
st.dataframe(
    df[["name", "distance_km", "speed_kmh", "start_date"]]
    .sort_values("start_date", ascending=False)
    .head(10)
)


# ── Seção 10: Análise detalhada por atividade ────────────────────────────────
st.subheader("🔍 Análise detalhada por atividade")

df["label"]         = df["name"] + " - " + df["start_date"].dt.strftime("%d/%m/%Y")
atividade_escolhida = st.selectbox("Selecione uma atividade", df["label"])
atividade_id        = df[df["label"] == atividade_escolhida]["id"].values[0]

streams      = get_activity_streams(atividade_id)
polyline_map = get_activity_map(atividade_id)

if polyline_map:
    st.subheader("🗺️ Mapa do percurso")
    render_mapa(polyline_map, streams)

st.info(analisar_atividade(streams))

st.subheader("📈 Velocidade ao longo do percurso")
render_velocidade_fadiga(detectar_zonas_fadiga(streams))


# ── Seção 11: Zonas de treino ─────────────────────────────────────────────────
st.subheader("🫀 Zonas de Treino Z1–Z5")
st.caption(
    f"Calculado com FC máx = **{fc_max} bpm** e FTP = **{ftp} W**. "
    "Ajuste os valores na sidebar."
)

zonas = calcular_zonas(streams, fc_max=fc_max, ftp=ftp)
render_zonas_treino(zonas)


# ── Seção 12: Zonas por velocidade ───────────────────────────────────────────
st.subheader("🚴 Zonas de Treino por Velocidade")
st.caption(
    "Aproximação das zonas Z1–Z5 usando velocidade como proxy de intensidade. "
    "Útil quando não há sensor de FC ou potência."
)

vel_max_kmh = round(df["speed_kmh"].max(), 1)
df_zonas_vel = calcular_zonas_velocidade(streams, vel_max_kmh)
render_zonas_velocidade(df_zonas_vel, vel_max_kmh)


# ── Seção 13: Zonas por FTP estimado ─────────────────────────────────────────
st.subheader("⚡ Zonas de Potência com FTP Estimado")
st.caption(
    "O FTP é estimado automaticamente a partir da melhor velocidade média "
    "sustentada por 20 minutos contínuos nas suas últimas 20 atividades."
)

with st.spinner("Calculando FTP estimado..."):
    ftp_kmh = estimar_ftp_velocidade(df, get_activity_streams)

if ftp_kmh is None:
    st.warning("Não foi possível estimar o FTP — atividades sem dados suficientes.")
else:
    st.success(f"⚡ FTP estimado: **{ftp_kmh} km/h**")
    df_zonas_ftp = calcular_zonas_ftp_estimado(streams, ftp_kmh)
    render_zonas_ftp_estimado(df_zonas_ftp, ftp_kmh)

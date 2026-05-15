import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
import polyline
from streamlit_folium import st_folium
from branca.colormap import LinearColormap
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from utils import load_activities, gerar_analise, analisar_atividade
from strava_client import get_activity_streams, get_activity_map


# ================================================================
# CONFIGURAÇÃO DA PÁGINA
# (deve ser a primeira chamada Streamlit do script)
# ================================================================

st.set_page_config(page_title="Dashboard Ciclismo", layout="wide")


# ================================================================
# ESTILO
# ================================================================

def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# ================================================================
# TEMA PLOTLY
# ================================================================

def aplicar_tema_plotly(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white", size=14),
        title_font=dict(size=24, color="#FC5200"),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(gridcolor="#30363d", zeroline=False),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


# ================================================================
# CARREGAMENTO E PRÉ-PROCESSAMENTO DOS DADOS
# ================================================================

if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()

data = load_activities()
df = pd.DataFrame(data)

df = df[df["type"] == "Ride"].copy()
df["start_date"]      = pd.to_datetime(df["start_date"]).dt.tz_localize(None)
df["distance_km"]     = df["distance"] / 1000
df["moving_time_min"] = df["moving_time"] / 60
df["speed_kmh"]       = df["average_speed"] * 3.6


# ================================================================
# SIDEBAR — FILTRO DE PERÍODO
# ================================================================

st.sidebar.header("📅 Filtro de Período")

periodo = st.sidebar.selectbox(
    "Selecione o período",
    ["Tudo", "7 dias", "30 dias", "90 dias", "180 dias", "365 dias", "Personalizado"],
)

if periodo == "Personalizado":
    dias_custom = st.sidebar.number_input(
        "Digite a quantidade de dias", min_value=1, max_value=2000, value=30
    )
    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias_custom)
    df = df[df["start_date"] >= data_limite]

elif periodo != "Tudo":
    dias = int(periodo.split()[0])
    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias)
    df = df[df["start_date"] >= data_limite]
    st.sidebar.info(f"📊 Exibindo dados desde {data_limite.date()}")

else:
    st.sidebar.info("📊 Exibindo todos os dados disponíveis")


# ================================================================
# TÍTULO
# ================================================================

st.title("🚴‍♂️ Dashboard de Ciclismo - Strava")


# ================================================================
# SEÇÃO 1 — KPIs GERAIS
# ================================================================

st.subheader("📊 Resumo do período")

dist_total = round(df["distance_km"].sum(), 2)
tempo_total = (round(df["moving_time_min"].sum(), 2))/60
vel_media = round(df["speed_kmh"].mean(), 2)
alt_total = round(df["total_elevation_gain"].sum(), 2)

col1, col2, col3, col4 = st.columns(4)

kpis = [
    (col1, "🚴", "Distância Total",   f"{dist_total} km"),
    (col2, "🕒", "Tempo Total",       f"{tempo_total:.1f} h"),
    (col3, "⚡", "Velocidade Média",  f"{vel_media} km/h"),
    (col4, "⛰️", "Altimetria",        f"{alt_total} m"),
]

for col, icon, title, value in kpis:
    with col:
        st.markdown(f'''
        <div class="card">
            <div class="card-icon">{icon}</div>
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
        </div>
        ''', unsafe_allow_html=True)


# ================================================================
# SEÇÃO 2 — RECORDES PESSOAIS (PRs)
# ================================================================

st.subheader("🏆 Recordes pessoais")

pr_distancia  = df["distance_km"].max()
pr_velocidade = df["speed_kmh"].max()
pr_altimetria = df["total_elevation_gain"].max()
pr_tempo_h    = df["moving_time_min"].max() / 60

col1, col2, col3, col4 = st.columns(4)

prs = [
    (col1, "🏆", "PR Distância",  f"{pr_distancia:.1f} km"),
    (col2, "⚡", "PR Velocidade", f"{pr_velocidade:.1f} km/h"),
    (col3, "⛰️", "KOM Subida",    f"{pr_altimetria:.0f} m"),
    (col4, "🚴", "Longão",        f"{pr_tempo_h:.1f} h"),
]

for col, icon, title, value in prs:
    with col:
        st.markdown(f'''
        <div class="pr-card">
            <div class="pr-icon">{icon}</div>
            <div class="pr-title">{title}</div>
            <div class="pr-value">{value}</div>
        </div>
        ''', unsafe_allow_html=True)


# ================================================================
# SEÇÃO 3 — EVOLUÇÃO DE DISTÂNCIA
# ================================================================

st.subheader("📈 Evolução de distância ao longo do tempo")

df_group = df.groupby(df["start_date"].dt.date)["distance_km"].sum().reset_index()
df_group["acumulado"] = df_group["distance_km"].cumsum()

fig_line = px.line(df_group, x="start_date", y=["distance_km", "acumulado"], markers=True)
st.plotly_chart(aplicar_tema_plotly(fig_line), use_container_width=True)


# ================================================================
# SEÇÃO 4 — VOLUME SEMANAL + PREVISÃO (ML)
# ================================================================

st.subheader("📅 Volume semanal + previsão (Machine Learning)")

df["week"] = df["start_date"].dt.to_period("W").apply(lambda r: r.start_time)
df_week = df.groupby("week")["distance_km"].sum().reset_index().sort_values("week")

previsao = None  # usado nas seções seguintes

if len(df_week) >= 4:
    df_week["t"] = np.arange(len(df_week))
    X = df_week[["t"]]
    y = df_week["distance_km"]

    poly  = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)

    model = LinearRegression().fit(X_poly, y)

    next_t   = np.array([[df_week["t"].max() + 1]])
    previsao = model.predict(poly.transform(next_t))[0]

    proxima_semana = df_week["week"].max() + pd.Timedelta(days=7)

    df_previsao = pd.DataFrame({
        "week":        [proxima_semana],
        "distance_km": [previsao],
        "tipo":        ["Previsão"],
    })

    df_week["trend"] = model.predict(X_poly)
    df_week["tipo"]  = "Real"
    df_plot = pd.concat([df_week, df_previsao])

else:
    df_week["tipo"] = "Real"
    df_plot = df_week

df_plot = df_plot.tail(20)

fig_week = px.line(df_plot, x="week", y="distance_km", color="tipo", markers=True)

if "trend" in df_week.columns:
    fig_week.add_scatter(
        x=df_week["week"].tail(20),
        y=df_week["trend"].tail(20),
        mode="lines",
        name="Tendência (ML)",
        line=dict(dash="dot"),
    )

fig_week.update_traces(
    selector=dict(name="Previsão"),
    marker=dict(size=12, symbol="diamond"),
    line=dict(dash="dash"),
)

st.plotly_chart(aplicar_tema_plotly(fig_week), use_container_width=True)


# ================================================================
# SEÇÃO 5 — INSIGHTS SEMANAIS
# ================================================================

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


# ================================================================
# SEÇÃO 6 — METAS E PLANO SEMANAL
# ================================================================

st.subheader("🎯 Metas e plano semanal")

if previsao is not None and len(df_week) >= 4:
    ultima_semana = df_week.iloc[-1]["distance_km"]
    meta_final    = (ultima_semana * 1.10 + previsao) / 2

    # Classificação da meta
    aumento_pct = ((meta_final - ultima_semana) / ultima_semana) * 100 if ultima_semana else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success(f"🎯 Meta semanal: {meta_final:.2f} km")
        diff = meta_final - ultima_semana
        label = f"📈 +{diff:.2f} km" if diff > 0 else f"📉 {abs(diff):.2f} km"
        st.info(label)

    with col2:
        meta_mensal = meta_final * 4.3
        st.success(f"📅 Meta mensal: {meta_mensal:.2f} km")

    with col3:
        if aumento_pct <= 5:
            st.info("🟢 Meta leve (segura)")
        elif aumento_pct <= 15:
            st.warning("🟡 Meta moderada (desafiadora)")
        else:
            st.error("🔴 Meta agressiva")

    # Plano semanal
    st.subheader("📅 Plano semanal automático")

    proporcoes = {"Seg": 0, "Ter": 0.20, "Qua": 0.25, "Qui": 0, "Sex": 0.15, "Sáb": 0.25, "Dom": 0.15}
    df_plano   = pd.DataFrame([{"Dia": d, "KM": meta_final * p} for d, p in proporcoes.items()])

    st.dataframe(df_plano)
    fig_plano = px.bar(df_plano, x="Dia", y="KM")
    st.plotly_chart(aplicar_tema_plotly(fig_plano), use_container_width=True)

    # Análise avançada de risco
    st.subheader("🧠 Análise avançada de treino")

    ultimas_4 = df_week.tail(4)["distance_km"].values
    ultima    = ultimas_4[-1]
    media     = np.mean(ultimas_4[:-1])
    variacao  = ((ultima - media) / media) * 100 if media != 0 else 0
    desvio    = np.std(ultimas_4)

    col1, col2, col3 = st.columns(3)

    with col1:
        if variacao > 30:
            st.error("🚨 Possível overtraining")
        elif variacao > 15:
            st.warning("⚠️ Volume alto recente")
        else:
            st.success("✅ Volume controlado")

    with col2:
        if variacao > 40:
            st.error("🛑 Alto risco de lesão")
        elif variacao > 25:
            st.warning("⚠️ Risco moderado de lesão")
        else:
            st.info("🟢 Risco baixo de lesão")

    with col3:
        if desvio < 10:
            fator = 1.10
            st.success("Alta consistência")
        elif desvio < 25:
            fator = 1.05
            st.info("Consistência moderada")
        else:
            fator = 0.95
            st.warning("Baixa consistência")

    meta_ajustada = meta_final * fator
    st.success(f"⚙️ Meta ajustada pela consistência: {meta_ajustada:.2f} km")


# ================================================================
# SEÇÃO 7 — ANÁLISE INTELIGENTE SEMANAL
# ================================================================

st.subheader("🧠 Análise inteligente dos treinos")
st.info(gerar_analise(df))


# ================================================================
# SEÇÃO 8 — GRÁFICOS POR PEDAL
# ================================================================

st.subheader("🚴‍♂️ Análise por pedal")

df_pedal = df.sort_values("start_date")

col_esq, col_dir = st.columns(2)

with col_esq:
    st.markdown("**📏 Distância por pedal**")
    fig_dist = px.bar(df_pedal, x="start_date", y="distance_km")
    st.plotly_chart(aplicar_tema_plotly(fig_dist), use_container_width=True)

with col_dir:
    st.markdown("**⚡ Velocidade por pedal**")
    fig_speed = px.line(df_pedal, x="start_date", y="speed_kmh", markers=True)
    st.plotly_chart(aplicar_tema_plotly(fig_speed), use_container_width=True)

st.markdown("**⛰️ Elevação por pedal**")
fig_elev = px.bar(df_pedal, x="start_date", y="total_elevation_gain")
st.plotly_chart(aplicar_tema_plotly(fig_elev), use_container_width=True)


# ================================================================
# SEÇÃO 9 — TABELA DE ATIVIDADES
# ================================================================

st.subheader("📋 Últimos pedais")

st.dataframe(
    df[["name", "distance_km", "speed_kmh", "start_date"]]
    .sort_values(by="start_date", ascending=False)
    .head(10)
)


# ================================================================
# SEÇÃO 10 — ANÁLISE DETALHADA POR ATIVIDADE
# ================================================================

st.subheader("🔍 Análise detalhada por atividade")

df["label"] = df["name"] + " - " + df["start_date"].dt.strftime("%d/%m/%Y")

atividade_escolhida = st.selectbox(
    "Selecione uma atividade", df["label"], key="atividade_detalhada"
)

atividade_id = df[df["label"] == atividade_escolhida]["id"].values[0]

streams      = get_activity_streams(atividade_id)
polyline_map = get_activity_map(atividade_id)


# --- Mapa do percurso ---

if polyline_map:
    st.subheader("🗺️ Mapa Premium do Percurso")

    pontos         = polyline.decode(polyline_map)
    velocidade_raw = streams["velocity_smooth"]["data"]
    velocidade_kmh = [v * 3.6 for v in velocidade_raw]

    vmin, vmax = min(velocidade_kmh), max(velocidade_kmh)
    colormap   = LinearColormap(colors=["red", "yellow", "green"], vmin=vmin, vmax=vmax)
    colormap.caption = "Velocidade (km/h)"

    mapa = folium.Map(location=pontos[0], zoom_start=13, tiles="CartoDB dark_matter")

    for i in range(len(pontos) - 1):
        cor = colormap(velocidade_kmh[min(i, len(velocidade_kmh) - 1)])
        folium.PolyLine([pontos[i], pontos[i + 1]], color=cor, weight=5, opacity=0.9).add_to(mapa)

    folium.Marker(pontos[0],  tooltip="Início", icon=folium.Icon(color="green", icon="play")).add_to(mapa)
    folium.Marker(pontos[-1], tooltip="Fim",    icon=folium.Icon(color="red",   icon="stop")).add_to(mapa)
    colormap.add_to(mapa)

    st_folium(mapa, width=1200, height=600, returned_objects=[])


# --- Análise textual ---

st.info(analisar_atividade(streams))


# --- Gráfico de velocidade com zonas de fadiga ---

st.subheader("📈 Velocidade ao longo do percurso")

velocidade_kmh = [v * 3.6 for v in streams["velocity_smooth"]["data"]]
dist_km        = [d / 1000  for d in streams["distance"]["data"]]
n              = len(velocidade_kmh)

inicio_idx = int(n * 0.25)
ritmo_base = sum(velocidade_kmh[:inicio_idx]) / inicio_idx

fadiga_index = None
quebra_index = None

for i in range(inicio_idx, n - 15):
    trecho = velocidade_kmh[i : i + 15]
    if not fadiga_index and all(v < ritmo_base * 0.85 for v in trecho):
        fadiga_index = i
    if all(v < ritmo_base * 0.50 for v in trecho):
        quebra_index = i
        break

# Pacing ideal
trecho_bom     = velocidade_kmh[:fadiga_index] if fadiga_index else velocidade_kmh[: int(n * 0.3)]
trecho_filtrado = [v for v in trecho_bom if 8 < v < 25]
limite_superior = np.percentile(trecho_filtrado, 90)
trecho_filtrado = [v for v in trecho_filtrado if v <= limite_superior]
pacing_ideal    = np.median(trecho_filtrado)

fig = go.Figure()
fig.add_trace(go.Scatter(x=dist_km, y=velocidade_kmh, mode="lines", name="Velocidade (km/h)"))

if fadiga_index:
    fig.add_vrect(x0=dist_km[fadiga_index], x1=dist_km[fadiga_index] + 3,
                  fillcolor="yellow", opacity=0.2, line_width=0)
    fig.add_trace(go.Scatter(
        x=[dist_km[fadiga_index]], y=[velocidade_kmh[fadiga_index]],
        mode="markers+text", text=["🟡 Fadiga"], textposition="top center",
        marker=dict(size=10, color="yellow"), name="Fadiga",
    ))

if quebra_index:
    fig.add_vrect(x0=dist_km[quebra_index], x1=dist_km[quebra_index] + 5,
                  fillcolor="red", opacity=0.2, line_width=0)
    fig.add_trace(go.Scatter(
        x=[dist_km[quebra_index]], y=[velocidade_kmh[quebra_index]],
        mode="markers+text", text=["🔴 Quebra"], textposition="top center",
        marker=dict(size=12, color="red"), name="Quebra",
    ))

fig.add_hline(y=sum(velocidade_kmh) / n, line_dash="dash",  line_color="orange",
              line_width=3, annotation_text="Média",        annotation_position="top right")
fig.add_hline(y=pacing_ideal,             line_dash="dot",   line_color="green",
              line_width=3, annotation_text="Pacing Ideal", annotation_position="bottom right")

fig.update_layout(title="📈 Velocidade ao longo do percurso",
                  xaxis_title="Distância (km)", yaxis_title="Velocidade (km/h)",
                  hovermode="x unified")

st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)

# --- Diagnóstico textual ---

if fadiga_index and quebra_index:
    st.warning(f"""
⚠️ Fadiga iniciou por volta de {dist_km[fadiga_index]:.1f} km
🔴 Quebra consolidada após {dist_km[quebra_index]:.1f} km

👉 Sugestão: controlar melhor o ritmo inicial para evitar queda de desempenho
""")

st.success(f"""
🎯 **Pacing Ideal estimado: {pacing_ideal:.1f} km/h**

👉 Esse é o ritmo que você poderia manter para evitar a quebra.

💡 Estratégia:
- Comece entre {pacing_ideal - 1:.1f} e {pacing_ideal:.1f} km/h
- Evite picos acima de {pacing_ideal + 2:.1f} km/h no início
""")

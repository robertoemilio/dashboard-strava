import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from utils import load_activities
from utils import gerar_analise #adicionei essa linha Roberto - 30-03-2026 para gerar uma espeicie de IA


from strava_client import get_activity_streams, get_activity_map
from utils import analisar_atividade
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import polyline
from branca.colormap import LinearColormap
import numpy as np

# =========================
# PARA LER O CSS
# =========================
def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
#---------------------------------------

# =========================
# TEMA DOS GRÁFICOS PLOTLY
# =========================
def aplicar_tema_plotly(fig):

    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",

        font=dict(
            color="white",
            size=14
        ),

        title_font=dict(
            size=24,
            color="#FC5200"
        ),

        legend=dict(
            bgcolor="#161b22",
            bordercolor="#30363d",
            borderwidth=1
        ),

        xaxis=dict(
            showgrid=False,
            zeroline=False
        ),

        yaxis=dict(
            gridcolor="#30363d",
            zeroline=False
        ),

        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig
#---------------------------------------

# =========================
# SPARKLINE
# =========================

def gerar_sparkline(data):

    blocks = "▁▂▃▄▅▆▇█"

    mn = min(data)
    mx = max(data)

    if mx - mn == 0:
        return blocks[0] * len(data)

    spark = ""

    for v in data:
        idx = int((v - mn) / (mx - mn) * (len(blocks)-1))
        spark += blocks[idx]

    return spark


#---------------------------------------

if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    
# =========================
# CONFIGURAÇÃO
# =========================
st.set_page_config(page_title="Dashboard Ciclismo", layout="wide")
st.title("🚴‍♂️ Dashboard de Ciclismo - Strava")

# =========================
# CARREGAR DADOS
# =========================
#data = load_activities()
@st.cache_data(ttl=600)
def get_data():
    return load_activities()

data = get_data()

df = pd.DataFrame(data)

df = df[df["type"] == "Ride"]
df["start_date"] = pd.to_datetime(df["start_date"]).dt.tz_localize(None)

df["distance_km"] = df["distance"] / 1000
df["moving_time_min"] = df["moving_time"] / 60
df["speed_kmh"] = df["average_speed"] * 3.6

# =========================
# FILTRO
# =========================
#st.sidebar.header("📅 Filtro de Período")

#periodo = st.sidebar.selectbox(
#    "Selecione o período",
#    ["Tudo", "7 dias", "30 dias", "90 dias"]
#)

#if periodo != "Tudo":
#    dias = int(periodo.split()[0])
#    data_limite = pd.Timestamp.now() - pd.Timedelta(days=dias)
#    df = df[df["start_date"] >= data_limite]


# =========================
# FILTRO DE PERÍODO (AVANÇADO)
# =========================
st.sidebar.header("📅 Filtro de Período")

opcoes = [
    "Tudo",
    "7 dias",
    "30 dias",
    "90 dias",
    "180 dias",
    "365 dias",
    "Personalizado"
]

periodo = st.sidebar.selectbox("Selecione o período", opcoes)

# =========================
# LÓGICA DO FILTRO
# =========================
if periodo == "Personalizado":
    dias_custom = st.sidebar.number_input(
        "Digite a quantidade de dias",
        min_value=1,
        max_value=2000,
        value=30
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
    
# se for "Tudo", não filtra



# =========================
# SPARKLINE DATA
# =========================

spark_data = df["distance_km"].tail(7).tolist()

sparkline = gerar_sparkline(spark_data)

# =========================
# KPIs
# =========================
#col1, col2, col3, col4 = st.columns(4)

#col1.metric("Distância Total (km)", round(df["distance_km"].sum(), 2))
#col2.metric("Tempo Total (min)", round(df["moving_time_min"].sum(), 2))
#col3.metric("Velocidade Média (km/h)", round(df["speed_kmh"].mean(), 2))
#col4.metric("Altimetria (m)", round(df["total_elevation_gain"].sum(), 2))

# =========================
# KPIs PREMIUM
# =========================

dist_total = round(df["distance_km"].sum(), 2)
tempo_total = round(df["moving_time_min"].sum(), 2)
vel_media = round(df["speed_kmh"].mean(), 2)
alt_total = round(df["total_elevation_gain"].sum(), 2)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f'''
    <div class="card">
        <div class="card-icon">🚴</div>
        <div class="card-title">Distância Total</div>
        <div class="card-value">{dist_total} km</div>
        <div class="sparkline">{sparkline}</div>
    </div>
    ''', unsafe_allow_html=True)

with col2:
    st.markdown(f'''
    <div class="card">
        <div class="card-icon">🕒</div>
        <div class="card-title">Tempo Total</div>
        <div class="card-value">{tempo_total} min</div>
        <div class="sparkline">{sparkline}</div>
    </div>
    ''', unsafe_allow_html=True)

with col3:
    st.markdown(f'''
    <div class="card">
        <div class="card-icon">⚡</div>
        <div class="card-title">Velocidade Média</div>
        <div class="card-value">{vel_media} km/h</div>
        <div class="sparkline">{sparkline}</div>
    </div>
    ''', unsafe_allow_html=True)

with col4:
    st.markdown(f'''
    <div class="card">
        <div class="card-icon">⛰️</div>
        <div class="card-title">Altimetria</div>
        <div class="card-value">{alt_total} m</div>
    </div>
    ''', unsafe_allow_html=True)


# =========================
# EVOLUÇÃO
# =========================
st.subheader("📈 Evolução de distância ao longo do tempo")

df_group = df.groupby(df["start_date"].dt.date)["distance_km"].sum().reset_index()
df_group["acumulado"] = df_group["distance_km"].cumsum()

fig_line = px.line(df_group, x="start_date", y=["distance_km", "acumulado"], markers=True)

fig_line = aplicar_tema_plotly(fig_line)

st.plotly_chart(fig_line, use_container_width=True)

# =========================
# ANÁLISE SEMANAL + ML
# =========================
st.subheader("📅 Volume semanal + previsão (Machine Learning)")

df["week"] = df["start_date"].dt.to_period("W").apply(lambda r: r.start_time)
df_week = df.groupby("week")["distance_km"].sum().reset_index()
df_week = df_week.sort_values("week")

if len(df_week) >= 4:
    df_week["t"] = np.arange(len(df_week))
    X = df_week[["t"]]
    y = df_week["distance_km"]

    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)

    model = LinearRegression()
    model.fit(X_poly, y)

    next_t = np.array([[df_week["t"].max() + 1]])
    previsao = model.predict(poly.transform(next_t))[0]

    proxima_semana = df_week["week"].max() + pd.Timedelta(days=7)

    df_previsao = pd.DataFrame({
        "week": [proxima_semana],
        "distance_km": [previsao],
        "tipo": ["Previsão"]
    })

    df_week["trend"] = model.predict(X_poly)
    df_week["tipo"] = "Real"
    df_plot = pd.concat([df_week, df_previsao])

else:
    df_week["tipo"] = "Real"
    df_plot = df_week

df_plot = df_plot.tail(20)

# =========================
# GRÁFICO
# =========================
fig_week = px.line(df_plot, x="week", y="distance_km", color="tipo", markers=True)

if "trend" in df_week.columns:
    fig_week.add_scatter(
        x=df_week["week"].tail(20),
        y=df_week["trend"].tail(20),
        mode="lines",
        name="Tendência (ML)",
        line=dict(dash="dot")
    )

fig_week.update_traces(
    selector=dict(name="Previsão"),
    marker=dict(size=12, symbol="diamond"),
    line=dict(dash="dash")
)

fig_week = aplicar_tema_plotly(fig_week)

st.plotly_chart(fig_week, use_container_width=True)

# =========================
# COMPARAÇÃO SEMANAL
# =========================
st.subheader("🧠 Comparação semanal")

if len(df_week) >= 2:
    ultima = df_week.iloc[-1]["distance_km"]
    anterior = df_week.iloc[-2]["distance_km"]

    variacao = ((ultima - anterior) / anterior * 100) if anterior != 0 else 0

    if variacao > 0:
        st.success(f"📈 {variacao:.1f}% a mais que semana passada")
    elif variacao < 0:
        st.warning(f"📉 {abs(variacao):.1f}% a menos")
    else:
        st.info("➡️ Mesmo volume")

# =========================
# TENDÊNCIA
# =========================
st.subheader("📊 Tendência de performance")

if len(df_week) >= 4:
    ultimas = df_week.tail(4)["distance_km"].values
    score = sum(
        1 if ultimas[i] > ultimas[i-1]
        else -1 if ultimas[i] < ultimas[i-1]
        else 0
        for i in range(1, len(ultimas))
    )

    if score >= 2:
        st.success("🔥 Tendência de evolução")
    elif score <= -2:
        st.error("⚠️ Tendência de queda")
    else:
        st.info("➡️ Tendência estável")

# =========================
# PREVISÃO
# =========================
st.subheader("🔮 Previsão")

if len(df_week) >= 4:
    ultima_semana = df_week.iloc[-1]["distance_km"]
    diff = previsao - ultima_semana

    st.success(f"{previsao:.2f} km")

    if diff > 0:
        st.success(f"📈 +{diff:.2f} km")
    else:
        st.warning(f"📉 {abs(diff):.2f} km")

# =========================
# META SEMANAL (COM INSIGHT)
# =========================
st.subheader("🎯 Meta semanal")

if len(df_week) >= 4:
    crescimento = 0.10
    meta = ultima_semana * (1 + crescimento)
    meta_final = (meta + previsao) / 2

    st.success(f"🎯 Meta sugerida: {meta_final:.2f} km")

    diff = meta_final - ultima_semana

    if diff > 0:
        st.info(f"📈 Aumentar cerca de {diff:.2f} km")
    elif diff < 0:
        st.warning(f"📉 Reduzir cerca de {abs(diff):.2f} km")
    else:
        st.info("➡️ Manter o volume")

    aumento_percentual = ((meta_final - ultima_semana) / ultima_semana) * 100

    if aumento_percentual <= 5:
        st.info("🟢 Meta leve (segura)")
    elif aumento_percentual <= 15:
        st.warning("🟡 Meta moderada (desafiadora)")
    else:
        st.error("🔴 Meta agressiva")

# =========================
# META MENSAL
# =========================
st.subheader("📅 Meta mensal")

if len(df_week) >= 4:
    meta_mensal = meta_final * 4.3
    st.success(f"{meta_mensal:.2f} km")

# =========================
# PLANO SEMANAL
# =========================
st.subheader("📅 Plano semanal automático")

if len(df_week) >= 4:
    plano = {
        "Seg": 0,
        "Ter": 0.20,
        "Qua": 0.25,
        "Qui": 0,
        "Sex": 0.15,
        "Sáb": 0.25,
        "Dom": 0.15
    }

    df_plano = pd.DataFrame([
        {"Dia": d, "KM": meta_final * p}
        for d, p in plano.items()
    ])

    st.dataframe(df_plano)
    fig_plano = px.bar(df_plano, x="Dia", y="KM")

fig_plano = aplicar_tema_plotly(fig_plano)

st.plotly_chart(fig_plano, use_container_width=True)

# =========================
# ANÁLISE AVANÇADA
# =========================
st.subheader("🧠 Análise inteligente de treino")

if len(df_week) >= 4:

    ultimas_4 = df_week.tail(4)["distance_km"].values
    ultima = ultimas_4[-1]
    media = np.mean(ultimas_4[:-1])

    variacao = ((ultima - media) / media) * 100 if media != 0 else 0

    if variacao > 30:
        st.error("🚨 Possível overtraining")
    elif variacao > 15:
        st.warning("⚠️ Volume alto recente")
    else:
        st.success("✅ Volume controlado")

    if variacao > 40:
        st.error("🛑 Alto risco de lesão")
    elif variacao > 25:
        st.warning("⚠️ Risco moderado")
    else:
        st.info("🟢 Risco baixo")

    desvio = np.std(ultimas_4)

    if desvio < 10:
        fator = 1.10
        st.success("Alta consistência")
    elif desvio < 25:
        fator = 1.05
        st.info("Consistência moderada")
    else:
        fator = 0.95
        st.warning("Baixa consistência")

    st.subheader("⚙️ Meta ajustada")

    meta_ajustada = meta_final * fator
    st.success(f"{meta_ajustada:.2f} km")

# =========================
# ANÁLISE AUTOMÁTICA DOS TREINOS - Roberto - 30-03-2026
# =========================

st.subheader("🧠 Análise Inteligente dos Treinos")

analise = gerar_analise(df)

st.info(analise)


# =========================
# NOVOS GRÁFICOS POR PEDAL
# =========================
st.subheader("🚴‍♂️ Análise por pedal")

#df_pedal = df.sort_values("start_date").tail(20) # essa linha pega apenas as ultimas 20 atividades
df_pedal = df.sort_values("start_date") # esta obedece o filtro ou seja se colocar todas vao todas atividades se for 7 dias vai todas dos ultimos 7 dias

st.subheader("📏 Distância por pedal")
fig_dist = px.bar(
    df_pedal,
    x="start_date",
    y="distance_km"
)

fig_dist = aplicar_tema_plotly(fig_dist)

st.plotly_chart(fig_dist, use_container_width=True)

st.subheader("⚡ Velocidade por pedal")
fig_speed = px.line(
    df_pedal,
    x="start_date",
    y="speed_kmh",
    markers=True
)

fig_speed = aplicar_tema_plotly(fig_speed)

st.plotly_chart(fig_speed, use_container_width=True)

st.subheader("⛰️ Elevação por pedal")
fig_elev = px.bar(
    df_pedal,
    x="start_date",
    y="total_elevation_gain"
)

fig_elev = aplicar_tema_plotly(fig_elev)

st.plotly_chart(fig_elev, use_container_width=True)

# =========================
# TABELA
# =========================
st.subheader("📋 Últimos pedais")

st.dataframe(
    df[["name", "distance_km", "speed_kmh", "start_date"]]
    .sort_values(by="start_date", ascending=False)
    .head(10)
)

# ===============================
# 🔍 ANÁLISE DETALHADA POR ATIVIDADE
# ===============================

st.subheader("🔍 Análise detalhada por atividade")

# Criar lista amigável
df["label"] = df["name"] + " - " + df["start_date"].dt.strftime("%d/%m/%Y")

atividade_escolhida = st.selectbox(
    "Selecione uma atividade",
    df["label"],
    key="atividade_detalhada"
)

# Pegar ID correto
atividade_id = df[df["label"] == atividade_escolhida]["id"].values[0]

# 🔹 AQUI entra o get_activity_streams
streams = get_activity_streams(atividade_id)

# ===============================
# 🗺️ MAPA PREMIU DO PEDAL
# ===============================

polyline_map = get_activity_map(atividade_id)

if polyline_map:

    pontos = polyline.decode(polyline_map)

    # ===============================
    # CRIAR MAPA DARK
    # ===============================

    mapa = folium.Map(
        location=pontos[0],
        zoom_start=13,
        tiles="CartoDB dark_matter"
    )

    # ===============================
    # HEATMAP POR VELOCIDADE
    # ===============================

    velocidade = streams["velocity_smooth"]["data"]

    velocidade_kmh = [v * 3.6 for v in velocidade]

    vmin = min(velocidade_kmh)
    vmax = max(velocidade_kmh)

    colormap = LinearColormap(
        colors=["red", "yellow", "green"],
        vmin=vmin,
        vmax=vmax
    )

    # ===============================
    # DESENHAR TRECHO COLORIDO
    # ===============================

    for i in range(len(pontos) - 1):

        cor = colormap(velocidade_kmh[min(i, len(velocidade_kmh)-1)])

        folium.PolyLine(
            [pontos[i], pontos[i+1]],
            color=cor,
            weight=5,
            opacity=0.9
        ).add_to(mapa)

   # ===============================
    # MARCADOR INÍCIO
    # ===============================

    folium.Marker(
        pontos[0],
        tooltip="Início",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(mapa)

    # ===============================
    # MARCADOR FINAL
    # ===============================

    folium.Marker(
        pontos[-1],
        tooltip="Fim",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(mapa)

    # ===============================
    # LEGENDA
    # ===============================

    colormap.caption = "Velocidade (km/h)"
    colormap.add_to(mapa)

    # ===============================
    # TÍTULO
    # ===============================

    st.subheader("🗺️ Mapa Premium do Percurso")

   # ===============================
    # EXIBIR MAPA
    # ===============================

    st_folium(
        mapa,
        width=1200,
        height=600,
        returned_objects=[]
    )



# 🔹 AQUI entra a análise
analise = analisar_atividade(streams)

st.info(analise)

# ===============================
# 📈 GRÁFICO DE PERFORMANCE
# ===============================

velocidade = streams["velocity_smooth"]["data"]
distancia = streams["distance"]["data"]

# Converter unidades
velocidade_kmh = [v * 3.6 for v in velocidade]
dist_km = [d / 1000 for d in distancia]


# ===============================
# 🔍 DETECTAR FADIGA E QUEBRA
# ===============================

n = len(velocidade_kmh)

inicio_idx = int(n * 0.25)

ritmo_base = sum(velocidade_kmh[:inicio_idx]) / inicio_idx

fadiga_index = None
quebra_index = None

for i in range(inicio_idx, n - 15):
    trecho = velocidade_kmh[i:i+15]

    # 🟡 Fadiga leve (queda inicial)
    if not fadiga_index and all(v < ritmo_base * 0.85 for v in trecho):
        fadiga_index = i

    # 🔴 Quebra real (queda forte)
    if all(v < ritmo_base * 0.50 for v in trecho):
        quebra_index = i
        break

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=dist_km,
    y=velocidade_kmh,
    mode='lines',
    name='Velocidade (km/h)'
))

# ===============================
# 🟡 ZONA DE FADIGA
# ===============================
if fadiga_index:
    fig.add_vrect(
        x0=dist_km[fadiga_index],
        x1=dist_km[fadiga_index] + 3,
        fillcolor="yellow",
        opacity=0.2,
        line_width=0,
    )

# ===============================
# 🔴 ZONA DE QUEBRA
# ===============================
if quebra_index:
    fig.add_vrect(
        x0=dist_km[quebra_index],
        x1=dist_km[quebra_index] + 5,
        fillcolor="red",
        opacity=0.2,
        line_width=0,
    )

# ===============================
# 🔴 MARCAR QUEBRA NO GRÁFICO
# ===============================

# 🟡 Fadiga
if fadiga_index:
    fig.add_trace(go.Scatter(
        x=[dist_km[fadiga_index]],
        y=[velocidade_kmh[fadiga_index]],
        mode='markers+text',
        text=["🟡 Fadiga"],
        textposition="top center",
        marker=dict(size=10, color="yellow"),
        name="Fadiga"
    ))

# 🔴 Quebra
if quebra_index:
    fig.add_trace(go.Scatter(
        x=[dist_km[quebra_index]],
        y=[velocidade_kmh[quebra_index]],
        mode='markers+text',
        text=["🔴 Quebra"],
        textposition="top center",
        marker=dict(size=12, color="red"),
        name="Quebra"
    ))

# ===============================
# 🎯 PACING IDEAL (VERSÃO FINAL)
# ===============================

if fadiga_index:
    trecho_bom = velocidade_kmh[:fadiga_index]
else:
    trecho_bom = velocidade_kmh[:int(len(velocidade_kmh)*0.3)]

# 1️⃣ filtro básico
trecho_filtrado = [v for v in trecho_bom if 8 < v < 25]

# 2️⃣ 👉 AQUI entra o que você perguntou
limite_superior = np.percentile(trecho_filtrado, 90)
trecho_filtrado = [v for v in trecho_filtrado if v <= limite_superior]

# 3️⃣ cálculo final
pacing_ideal = np.median(trecho_filtrado)

fig = aplicar_tema_plotly(fig)

fig.update_layout(
    title="📈 Velocidade ao longo do percurso",
    xaxis_title="Distância (km)",
    yaxis_title="Velocidade (km/h)",
    hovermode="x unified"
)

fig.add_hline(
    y=sum(velocidade_kmh)/len(velocidade_kmh),
    line_dash="dash",
    line_color="orange",
    line_width=3,
    annotation_text="Média",
    annotation_position="top right"
)

fig.add_hline(
    y=pacing_ideal,
    line_dash="dot",
    line_color="green",
    line_width=3,
    annotation_text="Pacing Ideal",
    annotation_position="bottom right"
)

st.plotly_chart(fig, use_container_width=True)


# ===============================
# 📊 TEXTO EXPLICATIVO
# ===============================
if fadiga_index and quebra_index:
    st.warning(f"""
⚠️ Fadiga iniciou por volta de {dist_km[fadiga_index]:.1f} km  
🔴 Quebra consolidada após {dist_km[quebra_index]:.1f} km  

👉 Sugestão: controlar melhor o ritmo inicial para evitar queda de desempenho
""")

# Pacing
st.success(f"""
🎯 **Pacing Ideal estimado: {pacing_ideal:.1f} km/h**

👉 Esse é o ritmo que você poderia manter para evitar a quebra.

📉 Você provavelmente começou acima desse ritmo, o que gerou fadiga progressiva.

💡 Estratégia:
- Comece entre {pacing_ideal - 1:.1f} e {pacing_ideal:.1f} km/h
- Evite picos acima de {pacing_ideal + 2:.1f} km/h no início
""")    


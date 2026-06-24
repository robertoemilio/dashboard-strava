import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.theme import aplicar_tema_plotly


def render_evolucao(df: pd.DataFrame) -> None:
    """Gráfico de linha: distância diária + acumulado."""
    df_group = df.groupby(df["start_date"].dt.date)["distance_km"].sum().reset_index()
    df_group["acumulado"] = df_group["distance_km"].cumsum()

    fig = px.line(df_group, x="start_date", y=["distance_km", "acumulado"], markers=True)
    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)


def render_volume_semanal(df_plot: pd.DataFrame, df_week: pd.DataFrame) -> None:
    """Gráfico de linha: volume semanal real, previsão e tendência ML."""
    fig = px.line(df_plot, x="week", y="distance_km", color="tipo", markers=True)

    if "trend" in df_week.columns:
        fig.add_scatter(
            x=df_week["week"].tail(20),
            y=df_week["trend"].tail(20),
            mode="lines",
            name="Tendência (ML)",
            line=dict(dash="dot"),
        )

    fig.update_traces(
        selector=dict(name="Previsão"),
        marker=dict(size=12, symbol="diamond"),
        line=dict(dash="dash"),
    )

    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)


def render_graficos_por_pedal(df: pd.DataFrame) -> None:
    """Gráficos de distância, velocidade e elevação por atividade."""
    df_pedal = df.sort_values("start_date")

    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.markdown("**📏 Distância por pedal**")
        fig = px.bar(df_pedal, x="start_date", y="distance_km")
        st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)

    with col_dir:
        st.markdown("**⚡ Velocidade por pedal**")
        fig = px.line(df_pedal, x="start_date", y="speed_kmh", markers=True)
        st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)

    st.markdown("**⛰️ Elevação por pedal**")
    fig = px.bar(df_pedal, x="start_date", y="total_elevation_gain")
    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)


def render_plano_semanal(meta_final: float) -> None:
    """Gráfico de barras com a distribuição do plano semanal."""
    proporcoes = {"Seg": 0, "Ter": 0.20, "Qua": 0.25, "Qui": 0, "Sex": 0.15, "Sáb": 0.25, "Dom": 0.15}
    df_plano   = pd.DataFrame([{"Dia": d, "KM": meta_final * p} for d, p in proporcoes.items()])

    st.dataframe(df_plano)
    fig = px.bar(df_plano, x="Dia", y="KM")
    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)


def render_velocidade_fadiga(zonas: dict) -> None:
    """
    Gráfico de linha de velocidade ao longo do percurso,
    com marcações de fadiga, quebra e pacing ideal.
    """
    velocidade_kmh = zonas["velocidade_kmh"]
    dist_km        = zonas["dist_km"]
    fadiga_index   = zonas["fadiga_index"]
    quebra_index   = zonas["quebra_index"]
    pacing_ideal   = zonas["pacing_ideal"]
    media_geral    = zonas["media_geral"]

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

    fig.add_hline(y=media_geral,   line_dash="dash", line_color="orange", line_width=3,
                  annotation_text="Média",        annotation_position="top right")
    fig.add_hline(y=pacing_ideal,  line_dash="dot",  line_color="green",  line_width=3,
                  annotation_text="Pacing Ideal", annotation_position="bottom right")

    fig.update_layout(title="📈 Velocidade ao longo do percurso",
                      xaxis_title="Distância (km)", yaxis_title="Velocidade (km/h)",
                      hovermode="x unified")

    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)

    # Diagnóstico textual
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


def render_zonas_treino(zonas: dict) -> None:
    """
    Renderiza os gráficos de zonas de treino (FC e/ou Potência).
    Mostra gráfico de rosca (percentual) + barra (tempo) para cada métrica.
    """
    tem_fc  = zonas.get("fc")       is not None
    tem_pot = zonas.get("potencia") is not None

    if not tem_fc and not tem_pot:
        st.warning("⚠️ Esta atividade não possui dados de FC nem de potência.")
        return

    metricas = []
    if tem_fc:
        metricas.append(("fc",       "❤️ Frequência Cardíaca", zonas["fc"]))
    if tem_pot:
        metricas.append(("potencia", "⚡ Potência (Watts)",    zonas["potencia"]))

    for _, titulo, df in metricas:
        st.markdown(f"### {titulo}")

        col_kpi = st.columns(5)
        for i, row in df.iterrows():
            col_kpi[i].markdown(f"""
            <div style="background:{row['cor']}22; border:1px solid {row['cor']};
                        border-radius:12px; padding:12px; text-align:center;">
                <div style="color:{row['cor']}; font-size:18px; font-weight:800;">
                    {row['zona']}
                </div>
                <div style="color:#8b949e; font-size:13px;">{row['nome']}</div>
                <div style="color:white; font-size:22px; font-weight:700;">
                    {row['percentual']}%
                </div>
                <div style="color:#8b949e; font-size:13px;">{row['tempo_str']}</div>
            </div>
            """, unsafe_allow_html=True)

        col_esq, col_dir = st.columns(2)

        # Rosca — percentual por zona
        with col_esq:
            fig_rosca = go.Figure(go.Pie(
                labels=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
                values=df["percentual"],
                hole=0.55,
                marker_colors=df["cor"].tolist(),
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value}%<extra></extra>",
            ))
            fig_rosca.update_layout(
                title="Distribuição por zona (%)",
                showlegend=False,
            )
            st.plotly_chart(aplicar_tema_plotly(fig_rosca), use_container_width=True)

        # Barra horizontal — tempo por zona
        with col_dir:
            fig_barra = go.Figure(go.Bar(
                x=df["tempo_s"],
                y=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
                orientation="h",
                marker_color=df["cor"].tolist(),
                text=df["tempo_str"],
                textposition="auto",
                hovertemplate="%{y}<br>%{text}<extra></extra>",
            ))
            fig_barra.update_layout(
                title="Tempo em cada zona",
                xaxis_title="Segundos",
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(aplicar_tema_plotly(fig_barra), use_container_width=True)

        st.divider()


def render_zonas_velocidade(df: pd.DataFrame, vel_max_kmh: float) -> None:
    """
    Renderiza os gráficos de zonas de treino calculadas por velocidade.
    Mesma estrutura visual de render_zonas_treino.
    """
    if df.empty:
        st.warning("Não foi possível calcular as zonas por velocidade.")
        return

    st.caption(f"Referência: velocidade máxima histórica = **{vel_max_kmh:.1f} km/h**")

    # Cards por zona
    col_kpi = st.columns(5)
    for i, (_, row) in enumerate(df.iterrows()):
        col_kpi[i].markdown(f"""
        <div style="background:{row['cor']}22; border:1px solid {row['cor']};
                    border-radius:12px; padding:12px; text-align:center;">
            <div style="color:{row['cor']}; font-size:18px; font-weight:800;">
                {row['zona']}
            </div>
            <div style="color:#8b949e; font-size:13px;">{row['nome']}</div>
            <div style="color:white; font-size:22px; font-weight:700;">
                {row['percentual']}%
            </div>
            <div style="color:#8b949e; font-size:13px;">{row['tempo_str']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_esq, col_dir = st.columns(2)

    # Rosca — percentual por zona
    with col_esq:
        fig_rosca = go.Figure(go.Pie(
            labels=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
            values=df["percentual"],
            hole=0.55,
            marker_colors=df["cor"].tolist(),
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value}%<extra></extra>",
        ))
        fig_rosca.update_layout(
            title="Distribuição por zona (%)",
            showlegend=False,
        )
        st.plotly_chart(aplicar_tema_plotly(fig_rosca), use_container_width=True)

    # Barra horizontal — tempo por zona
    with col_dir:
        fig_barra = go.Figure(go.Bar(
            x=df["tempo_s"],
            y=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
            orientation="h",
            marker_color=df["cor"].tolist(),
            text=df["tempo_str"],
            textposition="auto",
            hovertemplate="%{y}<br>%{text}<extra></extra>",
        ))
        fig_barra.update_layout(
            title="Tempo em cada zona",
            xaxis_title="Segundos",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(aplicar_tema_plotly(fig_barra), use_container_width=True)


def render_zonas_ftp_estimado(df: pd.DataFrame, ftp_kmh: float) -> None:
    """
    Renderiza as zonas Z1–Z5 calculadas com FTP estimado por velocidade.
    """
    if df.empty:
        st.warning("Não foi possível calcular as zonas com FTP estimado.")
        return

    st.caption(
        f"FTP estimado = **{ftp_kmh} km/h** "
        "(melhor média de 20 min contínuos × 0.95, nas últimas 20 atividades)"
    )

    col_kpi = st.columns(5)
    for i, (_, row) in enumerate(df.iterrows()):
        col_kpi[i].markdown(f"""
        <div style="background:{row['cor']}22; border:1px solid {row['cor']};
                    border-radius:12px; padding:12px; text-align:center;">
            <div style="color:{row['cor']}; font-size:18px; font-weight:800;">
                {row['zona']}
            </div>
            <div style="color:#8b949e; font-size:13px;">{row['nome']}</div>
            <div style="color:white; font-size:22px; font-weight:700;">
                {row['percentual']}%
            </div>
            <div style="color:#8b949e; font-size:13px;">{row['tempo_str']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_esq, col_dir = st.columns(2)

    with col_esq:
        fig_rosca = go.Figure(go.Pie(
            labels=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
            values=df["percentual"],
            hole=0.55,
            marker_colors=df["cor"].tolist(),
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value}%<extra></extra>",
        ))
        fig_rosca.update_layout(title="Distribuição por zona (%)", showlegend=False)
        st.plotly_chart(aplicar_tema_plotly(fig_rosca), use_container_width=True)

    with col_dir:
        fig_barra = go.Figure(go.Bar(
            x=df["tempo_s"],
            y=[f"{r['zona']} – {r['nome']}" for _, r in df.iterrows()],
            orientation="h",
            marker_color=df["cor"].tolist(),
            text=df["tempo_str"],
            textposition="auto",
            hovertemplate="%{y}<br>%{text}<extra></extra>",
        ))
        fig_barra.update_layout(
            title="Tempo em cada zona",
            xaxis_title="Segundos",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(aplicar_tema_plotly(fig_barra), use_container_width=True)

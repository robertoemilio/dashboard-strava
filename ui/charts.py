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


def render_evolucao_segmento(df: pd.DataFrame, nome_segmento: str) -> None:
    """
    Gráfico de evolução das passagens do atleta por um segmento.
    Mostra tempo real, tendência suavizada, PR e variação percentual.
    """
    if df.empty:
        st.warning("Nenhum esforço encontrado para este segmento.")
        return

    pr_row  = df[df["is_pr"]].iloc[0]
    n       = len(df)
    primeiro = df.iloc[0]["tempo_s"]
    ultimo   = df.iloc[-1]["tempo_s"]
    evolucao = ((ultimo - primeiro) / primeiro * 100) if primeiro else 0

    # ── Métricas resumo ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Passagens",    n)
    col2.metric("🏆 PR",        pr_row["tempo_str"], f"{pr_row['data'].strftime('%d/%m/%Y')}")
    col3.metric("Última",       df.iloc[-1]["tempo_str"])
    col4.metric("Evolução",     f"{abs(evolucao):.1f}%",
                delta=f"{'↓ melhorou' if evolucao < 0 else '↑ piorou'}",
                delta_color="normal" if evolucao < 0 else "inverse")

    # ── Gráfico principal ─────────────────────────────────────────────────────
    fig = go.Figure()

    # Linha de tempo real
    fig.add_trace(go.Scatter(
        x=df["data"], y=df["tempo_s"],
        mode="lines+markers",
        name="Tempo (s)",
        line=dict(color="#FC5200", width=2),
        customdata=df[["tempo_str", "velocidade"]],
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Tempo: %{customdata[0]}<br>Velocidade: %{customdata[1]} km/h<extra></extra>",
    ))

    # Tendência suavizada
    fig.add_trace(go.Scatter(
        x=df["data"], y=df["tendencia"],
        mode="lines",
        name="Tendência (média 3)",
        line=dict(color="#8b949e", width=2, dash="dot"),
    ))

    # Destaque do PR
    fig.add_trace(go.Scatter(
        x=[pr_row["data"]], y=[pr_row["tempo_s"]],
        mode="markers+text",
        name="🏆 PR",
        text=[f"🏆 {pr_row['tempo_str']}"],
        textposition="top center",
        marker=dict(size=14, color="gold", symbol="star"),
    ))

    fig.update_layout(
        title=f"📍 Evolução no segmento: {nome_segmento}",
        xaxis_title="Data",
        yaxis_title="Tempo (segundos)",
        yaxis=dict(autorange="reversed"),   # menor tempo = melhor = cima
        hovermode="x unified",
    )

    st.plotly_chart(aplicar_tema_plotly(fig), use_container_width=True)

    # ── Gráfico de variação percentual ───────────────────────────────────────
    if n > 1:
        df_var = df.dropna(subset=["variacao_pct"])
        cores  = ["green" if v < 0 else "red" for v in df_var["variacao_pct"]]

        fig_var = go.Figure(go.Bar(
            x=df_var["data"],
            y=df_var["variacao_pct"],
            marker_color=cores,
            customdata=df_var["tempo_str"],
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Variação: %{y:.1f}%<br>Tempo: %{customdata}<extra></extra>",
            name="Variação %",
        ))

        fig_var.update_layout(
            title="📊 Variação de tempo entre passagens",
            xaxis_title="Data",
            yaxis_title="Variação (%)",
            showlegend=False,
        )

        st.plotly_chart(aplicar_tema_plotly(fig_var), use_container_width=True)
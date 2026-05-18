import streamlit as st
import plotly.graph_objects as go


def load_css(path: str = "style.css") -> None:
    """Injeta o arquivo CSS no Streamlit."""
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def aplicar_tema_plotly(fig: go.Figure) -> go.Figure:
    """Aplica o tema dark padrão do dashboard a qualquer figura Plotly."""
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

import folium
import polyline as poly_lib
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium


def render_mapa(polyline_str: str, streams: dict) -> None:
    """
    Renderiza o mapa do percurso colorido por velocidade.
    Recebe o summary_polyline da atividade e os streams de velocidade.
    """
    pontos         = poly_lib.decode(polyline_str)
    velocidade_kmh = [v * 3.6 for v in streams["velocity_smooth"]["data"]]

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

import pandas as pd
from strava_client import get_activities

def load_activities():
    return get_activities()

# --- Adicionei esse ponto para gerar uma ANÁLISE AUTOMÁTICA DOS TREINOS - Roberto - 30-03-2026

def gerar_analise(df):
    if df.empty:
        return "Sem dados suficientes para análise."

    ultima_semana = df[df["start_date"] >= df["start_date"].max() - pd.Timedelta(days=7)]
    semana_anterior = df[
        (df["start_date"] < df["start_date"].max() - pd.Timedelta(days=7)) &
        (df["start_date"] >= df["start_date"].max() - pd.Timedelta(days=14))
    ]

    dist_ultima = ultima_semana["distance_km"].sum()
    dist_anterior = semana_anterior["distance_km"].sum()

    dias_ativos = ultima_semana["start_date"].dt.date.nunique()

    variacao = 0
    if dist_anterior > 0:
        variacao = ((dist_ultima - dist_anterior) / dist_anterior) * 100

    mensagem = "🧠 **Análise Inteligente**\n\n"

    # 📈 Evolução
    if variacao > 10:
        mensagem += f"📈 Você aumentou {variacao:.1f}% seu volume semanal.\n"
    elif variacao < -10:
        mensagem += f"📉 Seu volume caiu {abs(variacao):.1f}%.\n"
    else:
        mensagem += "📊 Seu volume está estável.\n"

    # 🚴 Frequência
    mensagem += f"🚴 Você pedalou {dias_ativos} dias na última semana.\n"

    # ⚠️ Overtraining
    if variacao > 30:
        mensagem += "⚠️ Risco de overtraining! Reduza intensidade.\n"

    # 💡 Recomendação
    mensagem += "\n💡 **Recomendação:**\n"

    if variacao > 20:
        mensagem += "Faça treinos leves ou descanso ativo nos próximos dias.\n"
    elif variacao < -20:
        mensagem += "Você pode aumentar o volume gradualmente.\n"
    else:
        mensagem += "Mantenha consistência — você está no caminho certo.\n"

    # 🎯 Meta sugerida
    meta_min = dist_ultima * 0.9
    meta_max = dist_ultima * 1.1

    mensagem += f"\n🎯 Meta sugerida: entre {meta_min:.1f} km e {meta_max:.1f} km na próxima semana.\n"

    return mensagem
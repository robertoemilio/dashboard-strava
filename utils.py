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

#------------------
#esse bloco coloquei para testar analise individual de atividade - Roberto - 01/04/2026
def analisar_atividade(streams):
    velocidade = streams["velocity_smooth"]["data"]
    distancia = streams["distance"]["data"]

    velocidade_kmh = [v * 3.6 for v in velocidade]

    # Dividir em 3 partes
    n = len(velocidade_kmh)
    inicio = velocidade_kmh[:n//3]
    meio = velocidade_kmh[n//3:2*n//3]
    fim = velocidade_kmh[2*n//3:]

    media_inicio = sum(inicio) / len(inicio)
    media_meio = sum(meio) / len(meio)
    media_fim = sum(fim) / len(fim)

    mensagem = "🚴 **Análise da atividade**\n\n"

    mensagem += f"Velocidade média geral: {sum(velocidade_kmh)/n:.1f} km/h\n\n"

    mensagem += f"📊 Início: {media_inicio:.1f} km/h\n"
    mensagem += f"📊 Meio: {media_meio:.1f} km/h\n"
    mensagem += f"📊 Final: {media_fim:.1f} km/h\n\n"

    # Detectar queda progressiva
    if media_fim < media_inicio * 0.85:
        # descobrir onde começou a queda real
        queda_index = None
        for i in range(len(velocidade_kmh)):
            if velocidade_kmh[i] < media_inicio * 0.8:
                queda_index = i
                break

        if queda_index:
            km_queda = distancia[queda_index] / 1000
            mensagem += f"📉 Queda consistente de performance por volta de {km_queda:.1f} km\n"
    else:
        mensagem += "💪 Ritmo consistente durante o treino\n"

    # Insight inteligente
    if media_meio > media_fim:
        mensagem += "\n⚠️ Indício de fadiga progressiva no final do treino\n"

    if media_inicio > media_meio:
        mensagem += "⚠️ Você pode ter começado forte demais\n"

    return mensagem
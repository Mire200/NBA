from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd
import time
import numpy as np

# Seuils à analyser
pts_thresholds = list(range(5, 35))       # 5.5 à 34.5
reb_thresholds = list(range(1, 21))       # 1.5 à 20.5
ast_thresholds = list(range(1, 21))       # 1.5 à 20.5
fg3_thresholds  = list(range(0, 11))      # 1.5 à 10.5

# Liste des joueurs actifs
active_players = players.get_active_players()
results = []

for player in active_players:
    player_name = player["full_name"]
    player_id = player["id"]

    try:
        # Récupérer les 5 derniers matchs
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='2024-25')
        df = gamelog.get_data_frames()[0].head(5)

        if df.empty:
            continue

        pts_list = df["PTS"].tolist()
        reb_list = df["REB"].tolist()
        ast_list = df["AST"].tolist()
        fg3_list = df["FG3M"].tolist()

        player_data = {"Joueur": player_name}
        player_data["\u00c9quipe"] = df["MATCHUP"].iloc[0].split(" ")[0]

        # Moyennes et écarts types
        player_data["Moy_PTS"] = round(np.mean(pts_list), 2)
        player_data["STD_PTS"] = round(np.std(pts_list), 2)

        player_data["Moy_REB"] = round(np.mean(reb_list), 2)
        player_data["STD_REB"] = round(np.std(reb_list), 2)

        player_data["Moy_AST"] = round(np.mean(ast_list), 2)
        player_data["STD_AST"] = round(np.std(ast_list), 2)

        player_data["Moy_3PM"] = round(np.mean(fg3_list), 2)
        player_data["STD_3PM"] = round(np.std(fg3_list), 2)

        # Paliers Points
        for t in pts_thresholds:
            label = f"{t+0.5} pts"
            player_data[label] = f"{sum(val >= t+0.5 for val in pts_list)}/5"

        # Paliers Rebonds
        for t in reb_thresholds:
            label = f"{t+0.5} reb"
            player_data[label] = f"{sum(val >= t+0.5 for val in reb_list)}/5"

        # Paliers Passes
        for t in ast_thresholds:
            label = f"{t+0.5} ast"
            player_data[label] = f"{sum(val >= t+0.5 for val in ast_list)}/5"

        # Paliers 3PM
        for t in fg3_thresholds:
            label = f"{t+0.5} 3pm"
            player_data[label] = f"{sum(val >= t+0.5 for val in fg3_list)}/5"

        results.append(player_data)
        print(f"✅ {player_name} traité")
        time.sleep(0.7)

    except Exception as e:
        print(f"❌ Erreur pour {player_name} : {e}")
        continue

# Export CSV
df_out = pd.DataFrame(results)
df_out.to_csv("nba_players_last5_paliers.csv", index=False)
print("✅ Fichier 'nba_players_last5_paliers.csv' généré avec moyennes et écarts types.")


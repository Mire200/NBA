import pandas as pd
import numpy as np
import re

# === MAPPINGS ÉQUIPES NBA ===
team_name_map = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM", "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS"
}
team_abbr_to_full = {v: k for k, v in team_name_map.items()}

# === OUTILS ===
def clean_name(name):
    return str(name).strip().lower()

def extract_opponent_team_mapped(match, player_team_abbr):
    try:
        team1_full, team2_full = match.split(" @ ")
        team1 = team_name_map.get(team1_full.strip())
        team2 = team_name_map.get(team2_full.strip())
        if player_team_abbr == team1:
            return team2
        elif player_team_abbr == team2:
            return team1
    except:
        return None

def get_defense_rank(df_def, team, stat_type, position):
    col = f"{position}_{'PTS' if stat_type == 'POINTS' else 'REB' if stat_type == 'REBOUNDS' else 'AST' if stat_type == 'ASSISTS' else '3P'}"
    row = df_def[df_def["Team"] == team]
    return int(row[col].values[0]) if not row.empty and col in row.columns else np.nan

def get_stat_row(df_stats, joueur):
    match = df_stats[df_stats["Joueur_clean"] == joueur]
    return match.iloc[0] if not match.empty else None

def estimate_success_proba(stat_row, stat_type, line):
    if stat_row is None:
        return np.nan
    suffix = {"POINTS": "pts", "REBOUNDS": "reb", "ASSISTS": "ast", "THREES": "3pm"}[stat_type]
    col = f"{line} {suffix}"
    if col in stat_row.index:
        match = re.search(r"(\d+)/5", str(stat_row[col]))
        if match:
            return int(match.group(1)) / 5
    return np.nan

def adjust_proba_aggressively(proba, defense_rank):
    if pd.isna(proba) or pd.isna(defense_rank):
        return np.nan
    if defense_rank <= 5: return proba * 0.80
    if defense_rank <= 10: return proba * 0.90
    if defense_rank <= 20: return proba
    if defense_rank <= 25: return proba * 1.10
    return proba * 1.20

# === MAIN FUNCTION ===
def generate_value_bets(props_file, pos_file, stats_file, defense_file):
    props = pd.read_csv(props_file)
    positions = pd.read_csv(pos_file)
    stats = pd.read_csv(stats_file)
    defense = pd.read_csv(defense_file)

    # Nettoyage noms joueurs
    props["Joueur_clean"] = props["Joueur"].apply(clean_name)
    positions["Joueur_clean"] = positions["Joueur"].apply(clean_name)
    stats["Joueur_clean"] = stats["Joueur"].apply(clean_name)

    # Fusion postes & équipes
    df = props.merge(positions[["Joueur_clean", "Poste"]], on="Joueur_clean", how="left")
    df = df.merge(stats[["Joueur_clean", "Équipe"]], on="Joueur_clean", how="left")

    # Équipe adverse
    df["Équipe adverse"] = df.apply(lambda row: extract_opponent_team_mapped(row["Match"], row["Équipe"]), axis=1)
    df["Équipe adverse nom complet"] = df["Équipe adverse"].map(team_abbr_to_full)

    # Classement défense
    df["Classement Déf"] = df.apply(
        lambda row: get_defense_rank(defense, row["Équipe adverse nom complet"], row["Type"], row["Poste"]),
        axis=1
    )

    # Moyenne / écart-type
    def get_moy_std(row):
        prefix = {"POINTS": "PTS", "REBOUNDS": "REB", "ASSISTS": "AST", "THREES": "3PM"}[row["Type"]]
        stat_row = get_stat_row(stats, row["Joueur_clean"])
        if stat_row is not None:
            return pd.Series([stat_row[f"Moy_{prefix}"], stat_row[f"STD_{prefix}"]])
        return pd.Series([np.nan, np.nan])

    df[["Moyenne", "Écart-type"]] = df.apply(get_moy_std, axis=1)

    # Probabilité brute
    df["Fréquence 5 matchs"] = df.apply(
        lambda row: estimate_success_proba(get_stat_row(stats, row["Joueur_clean"]), row["Type"], row["Ligne"]),
        axis=1
    )

    # Ajustements
    df["Proba ajustée"] = df.apply(lambda row: adjust_proba_aggressively(row["Fréquence 5 matchs"], row["Classement Déf"]), axis=1)
    df["Value ajustée"] = (df["Proba ajustée"] * df["Cote"]) - 1

    # Filtrage & export
    df_final = df[df["Value ajustée"] > 0].sort_values(by="Value ajustée", ascending=False)
    df_final.to_csv("value_bets_resultats.csv", index=False)
    print("\n✅ Fichier généré : value_bets_resultats.csv")

# === LANCEMENT ===
generate_value_bets(
    "player_props.csv",
    "NBA_Positions_.csv",
    "nba_players_last5_paliers.csv",
    "defense_vs_positions.csv"
)
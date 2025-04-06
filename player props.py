import requests
import pandas as pd
import time

API_KEY = "33f47af440012a9c9844143c68a3bc12"

# Étape 1 : Obtenir les événements NBA du jour
events_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/?apiKey={API_KEY}"
events_response = requests.get(events_url)

if events_response.status_code != 200:
    print("❌ Erreur en récupérant les événements NBA :", events_response.text)
    exit()

events = events_response.json()
print(f"✅ {len(events)} matchs NBA trouvés aujourd'hui.")

# Étape 2 : Boucle sur les events pour récupérer les props
all_props = []
markets = [
    "player_points",
    "player_rebounds",
    "player_assists",
    "player_threes",
    "player_steals",
    "player_blocks"
]

for event in events:
    event_id = event["id"]
    home = event["home_team"]
    away = event["away_team"]
    matchup = f"{away} @ {home}"

    odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds/"
    params = {
        "apiKey": API_KEY,
        "markets": ",".join(markets),
        "regions": "eu",
        "oddsFormat": "decimal"
    }

    odds_response = requests.get(odds_url, params=params)

    if odds_response.status_code != 200:
        print(f"⚠️ Erreur pour {matchup} :", odds_response.text)
        continue

    odds_data = odds_response.json()

    for bookmaker in odds_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            market_type = market["key"]
            prop_type = market_type.replace("player_", "").upper()

            for outcome in market["outcomes"]:
                player_name = outcome.get("description") or outcome.get("name") or "INCONNU"
                line = outcome.get("point")
                price = outcome.get("price")

                if player_name and line is not None and price:
                    all_props.append({
                        "Joueur": player_name,
                        "Match": matchup,
                        "Type": prop_type,
                        "Ligne": line,
                        "Cote": price,
                        "Bookmaker": bookmaker["title"]
                    })

    time.sleep(1)  # Anti-rate limit

# Étape 3 : Supprimer une ligne sur deux (supposée être Under)
df = pd.DataFrame(all_props)
df = df.iloc[::2].reset_index(drop=True)
df.to_csv("player_props.csv", index=False)
print("✅ Fichier 'player_props.csv' créé avec succès avec", len(df), "props (1 ligne sur 2 conservée).")



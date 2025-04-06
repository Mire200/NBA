import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

# === CONFIG ===
BANKROLL_INITIALE = 500.0
FICHIER_VALUE_BETS = "NBA/value_bets_resultats.csv"
FICHIER_HISTORIQUE = "historique_paris.csv"
FICHIER_PROPOSITIONS = "NBA/propositions_du_jour.csv"

st.set_page_config(page_title="Gestion Bankroll - Kelly", layout="wide")
st.title("📊 Gestion de Bankroll ")

@st.cache_data
def charger_csv(path):
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()  # Nettoyage des noms de colonnes
        return df
    except FileNotFoundError:
        return pd.DataFrame()

bets_df = charger_csv(FICHIER_VALUE_BETS)
historique_df = charger_csv(FICHIER_HISTORIQUE)

# === Bankroll actuelle ===
bankroll = historique_df["Bankroll_après"].iloc[-1] if not historique_df.empty else BANKROLL_INITIALE
st.sidebar.metric("💰 Bankroll actuelle", f"{bankroll:.2f} €")

# === Menu ===
page = st.sidebar.radio("Navigation", ["📋 Paris du jour", "📈 Résultats & Bilan"])

# === PAGE PARIS DU JOUR ===
if page == "📋 Paris du jour":
    st.header("📋 Paris suggérés aujourd'hui")
    taux_kelly = st.slider("Fraction de Kelly utilisée", 0.1, 1.0, 1.0, 0.1)

    propositions = []
    for _, row in bets_df.iterrows():
        proba = min(row.get("Proba ajustée", row.get("Proba", 0)), 1.0)
        value = row.get("Value ajustée", row.get("Value", 0))
        cote = row.get("Cote", None)

        if pd.isna(cote) or cote <= 1 or pd.isna(proba):
            continue

        edge = (cote * proba - 1) / (cote - 1)
        base_mise = bankroll * edge * taux_kelly

        min_ratio = 0.01
        max_ratio = 0.05
        ratio = min_ratio + (max_ratio - min_ratio) * proba
        plafond = bankroll * ratio
        mise = min(base_mise, plafond)
        mise = max(0, round(mise, 2))

        if mise > 0:
            propositions.append({
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Joueur": row.get("Joueur"),
                "Type": row.get("Type"),
                "Ligne": row.get("Ligne"),
                "Cote": cote,
                "Proba": round(proba, 3),
                "Value": round(value, 3),
                "Mise": mise,
                "Moyenne": row.get("Moyenne"),
                "Écart-type": row.get("Écart-type"),
                "Classement Déf": row.get("Classement Déf"),
                "Résultat": "en attente",
                "Profit": 0,
                "Bankroll_après": bankroll
            })

    propositions_df = pd.DataFrame(propositions)
    st.info(f"✅ Nombre de paris retenus : {len(propositions_df)}")

    # === Interface combiné ===
    st.subheader("🔗 Créer un pari combiné")
    selection = st.multiselect(
        "Sélectionne les paris à combiner :",
        options=propositions_df.index,
        format_func=lambda i: f"{propositions_df.loc[i, 'Joueur']} o{propositions_df.loc[i, 'Ligne']} @ {propositions_df.loc[i, 'Cote']}"
    )

    if selection:
        combi_cotes = [propositions_df.loc[i, "Cote"] for i in selection]
        combi_probas = [propositions_df.loc[i, "Proba"] for i in selection]
        combi_labels = [f"{propositions_df.loc[i, 'Joueur']} o{propositions_df.loc[i, 'Ligne']}" for i in selection]

        cote_combinee = round(pd.Series(combi_cotes).prod(), 2)
        proba_combinee = round(pd.Series(combi_probas).prod(), 4)
        value_combinee = round((cote_combinee * proba_combinee) - 1, 3)
        edge = (cote_combinee * proba_combinee - 1) / (cote_combinee - 1)
        base_mise = bankroll * edge * taux_kelly
        ratio = 0.01 + (0.05 - 0.01) * proba_combinee
        plafond = bankroll * ratio
        mise_combinee = max(0, round(min(base_mise, plafond), 2))

        st.markdown(f"""
        ✅ **Cote combinée :** {cote_combinee}  
        🎯 **Proba combinée :** {proba_combinee:.2%}  
        💎 **Value combinée :** {value_combinee:.3f}  
        💰 **Mise suggérée :** {mise_combinee:.2f} €
        """)

        if st.button("➕ Ajouter ce combiné"):
            new_row = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Joueur": "Combiné",
                "Type": "COMBINE",
                "Ligne": "-",
                "Cote": cote_combinee,
                "Proba": proba_combinee,
                "Value": value_combinee,
                "Mise": mise_combinee,
                "Résultat": "en attente",
                "Profit": 0,
                "Bankroll_après": bankroll,
                "Bookmaker": "Custom",
                "Moyenne": "",
                "Écart-type": "",
                "Classement Déf": "",
                "Détails combiné": " + ".join(combi_labels)
            }
            propositions_df = pd.concat([propositions_df, pd.DataFrame([new_row])], ignore_index=True)
            st.success("✅ Combiné ajouté à la liste des paris du jour.")

    colonnes_affichage = [col for col in [
        "Joueur", "Type", "Ligne", "Cote", "Proba", "Value", "Mise",
        "Moyenne", "Écart-type", "Classement Déf"
    ] if col in propositions_df.columns]

    st.dataframe(propositions_df[colonnes_affichage], use_container_width=True)

    if st.button("💾 Exporter les paris du jour"):
        propositions_df.to_csv(FICHIER_PROPOSITIONS, index=False)
        st.success("Fichier propositions_du_jour.csv exporté ✅")

# === PAGE BILAN ===
elif page == "📈 Résultats & Bilan":
    st.header("📈 Résultats & bilan")
    propositions_df = charger_csv(FICHIER_PROPOSITIONS)

    if propositions_df.empty:
        st.info("Aucun pari à afficher. Va d’abord sur 'Paris du jour' et clique sur 'Exporter'.")
    else:
        for idx, row in propositions_df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                st.markdown(f"**{row['Joueur']} - {row['Type']} o{row['Ligne']} @ {row['Cote']}**")
            with col2:
                result = st.selectbox(f"Résultat {idx+1}", ["en attente", "win", "loss"], key=f"res_{idx}")
            with col3:
                if result == "win":
                    profit = round(row["Mise"] * (row["Cote"] - 1), 2)
                elif result == "loss":
                    profit = -row["Mise"]
                else:
                    profit = 0
                new_bankroll = bankroll + profit

            if result != "en attente":
                new_entry = row.copy()
                new_entry["Résultat"] = result
                new_entry["Profit"] = profit
                new_entry["Bankroll_après"] = new_bankroll
                historique_df = pd.concat([historique_df, pd.DataFrame([new_entry])], ignore_index=True)
                bankroll = new_bankroll

        if st.button("✅ Enregistrer les résultats"):
            historique_df.to_csv(FICHIER_HISTORIQUE, index=False)
            st.success("Résultats enregistrés dans historique_paris.csv ✅")

    st.subheader("📊 Derniers paris")
    st.dataframe(historique_df.tail(10), use_container_width=True)

    if not historique_df.empty:
        st.subheader("📈 Courbe de bankroll")
        chart = alt.Chart(historique_df).mark_line().encode(
            x='Date:T',
            y='Bankroll_après:Q'
        ).properties(title="Évolution de la bankroll")
        st.altair_chart(chart, use_container_width=True)

        st.subheader("📊 Statistiques globales")
        total_bets = len(historique_df)
        bets_won = (historique_df["Résultat"] == "win").sum()
        bets_lost = (historique_df["Résultat"] == "loss").sum()
        total_profit = historique_df["Profit"].sum()
        total_mise = historique_df["Mise"].sum()
        roi = (total_profit / total_mise * 100) if total_mise > 0 else 0
        winrate = (bets_won / total_bets * 100) if total_bets > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("📈 ROI", f"{roi:.2f} %")
        col2.metric("✅ Winrate", f"{winrate:.2f} %")
        col3.metric("📊 Nombre de paris", f"{total_bets}")










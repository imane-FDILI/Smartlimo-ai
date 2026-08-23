"""
SmartLimo AI - Visualisation interactive d'un modèle NER (démo)

Lance une petite application web (via streamlit + spacy-streamlit) qui
permet de saisir du texte et de voir en direct les entités détectées par
un ou plusieurs modèles spaCy entraînés. Utile pour inspecter visuellement
la qualité d'un modèle de reconnaissance d'entités sans écrire de code.

Usage (via streamlit, pas directement avec python) :
    streamlit run visualize_model.py -- <modele1,modele2> "texte par defaut"
"""

import spacy_streamlit
import typer


def main(models: str, default_text: str):
    """models : liste de noms/chemins de modèles spaCy séparés par des
    virgules (ex: "en_core_web_sm,./training/model-best"), pour comparer
    plusieurs modèles côte à côte dans l'interface.
    default_text : texte pré-rempli affiché au chargement de la page."""
    # Découpe la chaîne "modele1, modele2" en liste ["modele1", "modele2"],
    # en retirant les espaces superflus autour de chaque nom.
    models = [name.strip() for name in models.split(",")]
    # N'affiche que le visualiseur "ner" (reconnaissance d'entités) ;
    # spacy-streamlit propose aussi "parser", "textcat", etc.
    spacy_streamlit.visualize(models, default_text, visualizers=["ner"])


if __name__ == "__main__":
    try:
        # typer.run interprète les arguments de la ligne de commande passés
        # après "--" par streamlit et les transmet à main(models, default_text).
        typer.run(main)
    except SystemExit:
        # streamlit relance ce script dans un contexte particulier où
        # typer peut déclencher un SystemExit après exécution normale :
        # on l'ignore pour ne pas faire planter l'application streamlit.
        pass

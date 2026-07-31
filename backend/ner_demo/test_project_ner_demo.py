"""
SmartLimo AI - Test d'intégration du projet spaCy de démo (ner_demo)

Ce test ne vérifie pas une fonction précise mais l'exécution complète du
"spaCy project" défini dans ce dossier (fichier project.yml, non montré
ici) : il télécharge les assets nécessaires puis exécute tous les workflows
définis (entraînement, évaluation...) ainsi que l'empaquetage du modèle
final. Sert de test de non-régression global sur la démo NER, à exécuter
avec pytest.
"""

from spacy.cli.project.run import project_run
from spacy.cli.project.assets import project_assets
from pathlib import Path


def test_ner_demo_project():
    """Reproduit ce qu'un utilisateur ferait manuellement en ligne de
    commande avec `spacy project` :
      1. project_assets   : télécharge/vérifie les fichiers de données
                             déclarés dans project.yml (ex: dataset brut).
      2. project_run(...,"all")     : exécute le workflow nommé "all"
                             (généralement : conversion des données,
                             entraînement, évaluation).
      3. project_run(...,"package") : empaquette le modèle entraîné dans
                             un format installable (wheel Python).
    Si l'une de ces étapes échoue, le test échoue - garantissant que
    l'ensemble du pipeline de la démo reste fonctionnel."""
    root = Path(__file__).parent
    project_assets(root)
    project_run(root, "all", capture=True)
    project_run(root, "package", capture=True)

"""Convert entity annotation from spaCy v2 TRAIN_DATA format to spaCy v3
.spacy format.

SmartLimo AI - Script utilitaire (démo NER) : les anciens outils
d'annotation (ex: interfaces d'annotation manuelle) produisent souvent des
données au format JSON "v2" (liste de tuples texte + positions
d'entités). spaCy v3 attend en revanche un format binaire optimisé
(.spacy, via DocBin). Ce script fait la conversion entre les deux.

Usage (ligne de commande, via typer) :
    python convert.py <lang> <input_path> <output_path>
ex : python convert.py en train_data.json train_data.spacy
"""
import srsly
import typer
import warnings
from pathlib import Path

import spacy
from spacy.tokens import DocBin


def convert(lang: str, input_path: Path, output_path: Path):
    """Lit les annotations au format v2 (JSON) depuis `input_path` et
    écrit un DocBin (.spacy) équivalent dans `output_path`.

    lang : code de langue (ex: "en") utilisé pour créer un pipeline spaCy
           "vierge" (spacy.blank), juste assez pour tokeniser le texte.
    """
    nlp = spacy.blank(lang)
    # DocBin est la structure de données spaCy optimisée pour stocker un
    # grand nombre de documents annotés de façon compacte sur disque.
    db = DocBin()
    # srsly.read_json lit le fichier ligne par ligne : chaque entrée est
    # un tuple (texte, dict d'annotations contenant la clé "entities").
    for text, annot in srsly.read_json(input_path):
        doc = nlp.make_doc(text)
        ents = []
        for start, end, label in annot["entities"]:
            # char_span convertit une position en caractères (start, end)
            # en un "span" de tokens. Cela peut échouer si les positions
            # ne tombent pas exactement sur une frontière de mot (ex: une
            # entité qui coupe un mot en plein milieu).
            span = doc.char_span(start, end, label=label)
            if span is None:
                # Impossible d'aligner cette entité sur des tokens entiers :
                # on l'ignore et on avertit plutôt que de faire planter
                # toute la conversion pour une seule annotation problématique.
                msg = f"Skipping entity [{start}, {end}, {label}] in the following text because the character span '{doc.text[start:end]}' does not align with token boundaries:\n\n{repr(text)}\n"
                warnings.warn(msg)
            else:
                ents.append(span)
        doc.ents = ents
        db.add(doc)
    db.to_disk(output_path)


if __name__ == "__main__":
    # typer.run expose automatiquement la fonction `convert` comme une
    # commande en ligne de commande, en déduisant les arguments (lang,
    # input_path, output_path) de sa signature.
    typer.run(convert)

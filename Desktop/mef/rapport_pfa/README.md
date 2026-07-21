# Rapport de Stage PFA — Instructions de compilation

## Structure du projet
```
rapport_pfa/
├── main.tex                    ← Document principal (point d'entrée)
├── README.md                   ← Ce fichier
├── chapters/
│   ├── 00_titlepage.tex        ← Page de garde officielle
│   ├── 01_remerciements.tex    ← Remerciements
│   ├── 02_resume.tex           ← Résumé (FR) + Abstract (EN)
│   ├── 03_introduction.tex     ← Introduction générale
│   ├── 04_organisme.tex        ← Chapitre 1 : Organisme d'accueil
│   ├── 05_contexte.tex         ← Chapitre 2 : Contexte du projet
│   ├── 06_conception.tex       ← Chapitre 3 : Analyse et conception
│   ├── 07_realisation.tex      ← Chapitre 4 : Réalisation
│   ├── 08_tests.tex            ← Chapitre 5 : Tests et résultats
│   ├── 09_conclusion.tex       ← Conclusion et perspectives
│   └── 10_annexes.tex          ← Annexes
├── bibliography/
│   └── references.bib          ← Références BibTeX
└── figures/                    ← Dossier pour images/captures d'écran
    └── .gitkeep                ← (voir commentaires dans .gitkeep)
```

## Compilation complète (pdflatex + bibtex)

```bash
pdflatex main.tex     # 1ère passe : génère les auxiliaires
bibtex   main         # Compile la bibliographie
pdflatex main.tex     # 2ème passe : intègre les références
pdflatex main.tex     # 3ème passe : résout les renvois croisés
```

### Avec latexmk (recommandé — automatise tout)
```bash
latexmk -pdf -bibtex main.tex
```

### Avec XeLaTeX (pour polices système)
```bash
latexmk -xelatex -bibtex main.tex
```

## Personnalisation rapide

1. **Informations générales** : Modifier les commandes `\newcommand` dans
   `main.tex` (section MÉTADONNÉES STAGE, vers la ligne 185).

2. **Chercher les placeholders** : 
   ```bash
   grep -rn "À COMPLÉTER" chapters/ main.tex
   ```

3. **Remplacer `\todo{...}`** : chaque occurrence `\todo{...}` indique
   un texte à rédiger. Remplacer par votre propre contenu.

4. **Ajouter des images** : placer les fichiers PNG/JPG dans `figures/`
   et décommenter les lignes `\includegraphics` dans les chapitres.

5. **Logo école / entreprise** : décommenter les lignes
   `\includegraphics[height=2.0cm]{figures/logo_school}` dans
   `chapters/00_titlepage.tex` et ajouter vos logos dans `figures/`.

## Packages requis
Inclus dans **TeX Live 2022+** ou **MiKTeX 23+** :

| Catégorie       | Packages                                              |
|-----------------|-------------------------------------------------------|
| Encodage/Langue | `inputenc`, `fontenc`, `babel`, `lmodern`, `microtype`|
| Mise en page    | `geometry`, `fancyhdr`, `emptypage`, `setspace`       |
| Couleurs        | `xcolor`                                              |
| Graphiques      | `graphicx`, `float`, `subfigure`, `tikz`              |
| Tableaux        | `booktabs`, `array`, `tabularx`, `multirow`, `longtable`|
| Listes          | `enumitem`                                            |
| Code source     | `listings`                                            |
| Titres          | `titlesec`, `titletoc`                                |
| Boîtes          | `tcolorbox` (most, skins, breakable, listings)        |
| Maths           | `amsmath`, `amssymb`                                  |
| Hyperliens      | `hyperref`, `bookmark`                                |
| Bibliographie   | `cite` (IEEE) ou `natbib` (APA)                       |

## Changer le style bibliographique

Pour passer du style **IEEE** au style **APA** :

1. Dans `main.tex`, remplacer :
   ```latex
   \usepackage{cite}
   ```
   par :
   ```latex
   \usepackage[authoryear,round]{natbib}
   ```

2. Et remplacer :
   ```latex
   \bibliographystyle{IEEEtran}
   ```
   par :
   ```latex
   \bibliographystyle{plainnat}
   ```

# Fiche d'Accomplissement — Instructions de compilation

## Structure
```
accomplissement/
└── main.tex          ← document unique auto-contenu
```

## Compiler (pdflatex)
```bash
pdflatex main.tex
pdflatex main.tex   # 2e passe pour les références internes
```
Ou en une commande :
```bash
pdflatex main.tex && pdflatex main.tex
```

## Personnalisation rapide
Ouvrez `main.tex` et modifiez les commandes dans la section
**INFORMATIONS STAGE** (vers la ligne 90) :
- `\StudentName` — Prénom et NOM de l'étudiant
- `\StudentField` — Filière / Spécialité
- `\CompanyName` — Nom de l'entreprise
- `\ProjectTitle` — Titre du projet
- etc.

Recherchez `[À COMPLÉTER` dans le fichier pour trouver tous les
emplacements à renseigner.

## Packages requis
Tous inclus dans TeX Live 2022+ ou MiKTeX 23+ :
`inputenc, fontenc, babel (french), lmodern, microtype,
geometry, fancyhdr, emptypage, parskip, xcolor (dvipsnames,table),
enumitem, booktabs, array, tabularx, multirow, graphicx, float,
tikz, titlesec, tcolorbox (most), hyperref`

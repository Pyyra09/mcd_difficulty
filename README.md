# MCD Difficulty Mod — Évaluateur de difficulté pour Minecraft Dungeons

Mod de données pour *Minecraft Dungeons* qui **évalue la difficulté d'un niveau** en
combinant la difficulté de base de la mission avec un **multiplicateur attribué à chaque
modificateur** (les « Affectors » internes du jeu : `mobDamageMul`, `mobHealthMul`,
`nightMode`, etc.).

Formule :

```
score = base_mission × multiplicateur_mode (ou niveau de menace Apocalypse+)
        × m₁ × m₂ × … × mₙ        (un multiplicateur par modificateur actif)
```

Si un modificateur actif a une magnitude différente de sa magnitude de référence
(ex. `mobDamageMul:200` au lieu de la référence 100), son bonus est mis à l'échelle
linéairement : `effectif = 1 + (multiplicateur − 1) × (magnitude / référence)`.

## Contenu

| Fichier | Rôle |
|---|---|
| `data/modifier_multipliers.json` | Multiplicateur de chaque modificateur + magnitude de référence |
| `data/difficulty_modes.json` | Multiplicateurs des modes Défaut / Aventure / Apocalypse / Apocalypse+ (niveaux 1–25) |
| `data/missions.json` | Difficulté de base de chaque mission |
| `scripts/evaluate.py` | Moteur d'évaluation + outil en ligne de commande (aucune dépendance) |

## Installation dans le jeu

Minecraft Dungeons n'a pas d'API de modding : les mods se font en modifiant les
fichiers de données contenus dans les archives PAK du jeu. Procédure générale :

1. **Décompresser les PAK** du jeu avec un outil communautaire (FModel, UModel/UE Viewer, ou `repak`).
2. **Fusionner** les tables de ce mod avec les données du jeu :
   - remplacez/étendez la table des Affectors par celle de `data/modifier_multipliers.json`
     (les clés correspondent aux noms internes `Affector` du jeu — cf. [Dungeons:Modifier sur le wiki](https://minecraft.wiki/w/Dungeons:Modifier)) ;
   - appliquez `data/difficulty_modes.json` et `data/missions.json` aux tables
     de difficulté/missions correspondantes.
3. **Repacker** l'archive PAK (même compression que l'original, en général zlib/Oodle)
   et la replacer dans `Minecraft Dungeons/Content/Paks/` (gardez une sauvegarde de l'original).
4. Lancez le jeu : les niveaux utiliseront les nouvelles valeurs.

> Les chemins exacts à l'intérieur des PAK varient selon la version du jeu ;
> repérez les fichiers JSON existants mentionnant les Affectors lors de l'étape 1
> et alignez la structure de ce mod dessus.

## Utilisation de l'outil d'évaluation

```bash
python3 scripts/evaluate.py --list
python3 scripts/evaluate.py --selftest

python3 scripts/evaluate.py --mission creeperwoods --mode apocalypse \
    --modifier mobDamageMul:200 --modifier nightMode

python3 scripts/evaluate.py --mission obsidianpinnacle --mode apocalypse_plus \
    --threat 25 --modifier mobHealthMul:200 --modifier instantGameOver

python3 scripts/evaluate.py --mission hm_spidercave --mode apocalypse \
    --modifier mobDamageMul:150 --modifier mobEnchantment
```

Exemple de sortie :

```json
{
  "mission": "obsidianpinnacle",
  "label": "Pic d'Obsidienne",
  "mode": "apocalypse_plus",
  "threat": 25,
  "base": 6.0,
  "mode_multiplier": 7.5,
  "modifiers": [
    { "modifier": "mobHealthMul", "magnitude": 200.0, "factor": 1.8 },
    { "modifier": "instantGameOver", "magnitude": null, "factor": 2.0 }
  ],
  "score": 162.0
}
```

## Difficulté de base : données extraites du jeu

Les valeurs de `data/missions.json` ne sont plus des estimations manuelles : elles sont
**calculées à partir des fichiers de niveaux réels du jeu** (`Dungeons/Content/data/lovika/levels/*.json`),
extraits des PAK fournis (pakchunk0 pour la base + secrets, pakchunk33–39 pour les DLC,
pakchunk80 pour la Grotte aux Araignées), déchiffrés avec la clé AES du jeu puis décompressés.

Pour chaque niveau, les métriques suivantes ont été extraites :

| Métrique | Clé du JSON de niveau |
|---|---|
| Étendues (longueur du niveau) | `stretches` |
| Donjons | `dungeons` |
| Groupes de mobs | `mob-groups` |
| Types de mobs distincts | `mob-groups[].types` |
| Défis | `challenges` |
| Densité de mobs | `default-mobs.density` |

Formule de la base (échelle 1–10, documentée dans `missions.json`) :

```
brut = étendues + 0.6×donjons + 0.15×types + 0.10×groupes + 0.08×défis   (× densité)
base = 1 + 9 × ÉchelleLog(brut), normalisée sur les missions story/dlc/secret
```

51 missions sont couvertes : histoire, DLC, missions secrètes, 11 chasses antiques
(`hm_*`, `ancientdungeons`) et la Tour. Sont exclues (non scorées) : `lobby`,
`menudummy` (aucun combat) et `netherhypermission-hyper` (tirage procédural non
décrit dans les JSON).

> **Limite assumée** : c'est un proxy structurel. Le jeu ne contient aucune table de
> difficulté en JSON — les valeurs officielles sont compilées dans les uassets/Blueprints
> (`BP_IngameGameMode`, DataTables). Les missions très scriptées (boss, ex. Pic
d'Obsidienne) peuvent être sous-estimées : ajustez leur champ `base` si besoin.

## Équilibrage des multiplicateurs

Les valeurs par défaut de `data/modifier_multipliers.json` sont un point de départ :

- **Modificateurs qui durcissent le niveau** (multiplicateur > 1) : `instantGameOver` (×2.0),
  `mobDamageMul` (×1.5), `mobHealthMul` (×1.4), `mobEnchantment` (×1.3), `nightMode` (×1.15)…
- **Modificateurs qui aident le joueur** (multiplicateur < 1) : `soulCountMul` (×0.85),
  `playerEnchantment` (×0.85), `emeraldHealthAdd` (×0.9), `playerSpeedMul` (×0.9)…

Ajustez les valeurs, relancez `--selftest` puis vos scénarios pour vérifier l'équilibre.

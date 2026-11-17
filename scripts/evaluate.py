#!/usr/bin/env python3
"""MCD Difficulty Mod - moteur d'évaluation.

Calcule la difficulté effective d'une mission :
    score = base_mission x multiplicateur_mode (ou niveau de menace)
            x produit des multiplicateurs de modificateurs actifs.

Chaque modificateur possède un multiplicateur de référence ; si le
modificateur actif a une magnitude (% d'effet) différente de sa magnitude
de référence, le bonus est mis à l'échelle linéairement :
    effectif = 1 + (multiplier - 1) x (magnitude / reference)

Usage :
    python3 evaluate.py --mission creeperwoods --mode apocalypse \\
        --modifier mobDamageMul:150 --modifier nightMode
    python3 evaluate.py --mission obsidianpinnacle --mode apocalypse_plus \\
        --threat 25 --modifier mobHealthMul:200 --modifier instantGameOver
    python3 evaluate.py --selftest
"""
import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def parse_modifier(arg):
    """'mobDamageMul:150' -> ('mobDamageMul', 150.0) ; 'nightMode' -> ('nightMode', None)."""
    if ":" in arg:
        key, _, raw = arg.partition(":")
        return key, float(raw)
    return arg, None


def modifier_factor(mods_cfg, key, magnitude):
    """Multiplicateur effectif d'un modificateur, mis à l'échelle par sa magnitude."""
    if key not in mods_cfg["modifiers"]:
        raise KeyError(f"Modificateur inconnu : {key}")
    cfg = mods_cfg["modifiers"][key]
    mult = cfg["multiplier"]
    if magnitude is None:
        return mult
    ref = cfg.get("reference_percent", 100.0)
    if cfg.get("per_stack"):
        return 1.0 + (mult - 1.0) * (magnitude / ref)
    if cfg.get("lower_is_harder"):
        scale = (ref - magnitude) / ref if ref else 1.0
    else:
        scale = magnitude / ref if ref else 1.0
    return 1.0 + (mult - 1.0) * scale


def evaluate(missions_cfg, modes_cfg, mods_cfg, mission_id, mode, threat=None, modifiers=()):
    missions = missions_cfg["missions"]
    if mission_id not in missions:
        raise KeyError(f"Mission inconnue : {mission_id}")
    base = missions[mission_id]["base"]

    modes = modes_cfg["modes"]
    if mode not in modes:
        raise KeyError(f"Mode inconnu : {mode}")
    mode_cfg = modes[mode]
    mode_mult = mode_cfg["multiplier"]
    if mode == "apocalypse_plus":
        levels = mode_cfg["threat_levels"]
        if threat is None:
            raise ValueError("Précisez --threat pour le mode apocalypse_plus (1-25).")
        if str(threat) not in levels:
            raise ValueError(f"Niveau de menace invalide : {threat} (1-25).")
        mode_mult = levels[str(threat)]

    total = base * mode_mult
    applied = []
    for arg in modifiers:
        key, magnitude = parse_modifier(arg)
        factor = modifier_factor(mods_cfg, key, magnitude)
        total *= factor
        applied.append({"modifier": key, "magnitude": magnitude, "factor": round(factor, 4)})

    return {
        "mission": mission_id,
        "label": missions[mission_id]["label"],
        "mode": mode,
        "threat": threat,
        "base": base,
        "mode_multiplier": mode_mult,
        "modifiers": applied,
        "score": round(total, 2),
    }


def selftest():
    missions = load("missions.json")
    modes = load("difficulty_modes.json")
    mods = load("modifier_multipliers.json")

    r1 = evaluate(missions, modes, mods, "creeperwoods", "default")
    assert r1["score"] == 8.9, r1

    r2 = evaluate(missions, modes, mods, "creeperwoods", "apocalypse",
                  modifiers=["mobDamageMul:200", "nightMode"])
    expected = 8.9 * 2.0 * 2.0 * 1.15
    assert abs(r2["score"] - round(expected, 2)) < 0.01, r2

    r3 = evaluate(missions, modes, mods, "obsidianpinnacle", "apocalypse_plus",
                  threat=25, modifiers=["mobHealthMul:200", "instantGameOver"])
    expected = 6.0 * 7.5 * 1.8 * 2.0
    assert abs(r3["score"] - round(expected, 2)) < 0.01, r3

    r4 = evaluate(missions, modes, mods, "soggyswamp", "adventure",
                  modifiers=["soulCountMul:300"])
    expected = 8.1 * 1.5 * (1.0 + (0.85 - 1.0) * (300 / 200))
    assert abs(r4["score"] - round(expected, 2)) < 0.01, r4

    print("Selftest OK")
    for r in (r1, r2, r3, r4):
        print(f"  {r['label']:<22} {r['mode']:<15} score={r['score']}")


def main():
    parser = argparse.ArgumentParser(description="Évalue la difficulté d'une mission MCD.")
    parser.add_argument("--mission", help="id de mission (ex: creeperwoods, hm_spidercave)")
    parser.add_argument("--mode", default="default",
                        help="default | adventure | apocalypse | apocalypse_plus")
    parser.add_argument("--threat", type=int, help="niveau de menace Apocalypse+ (1-25)")
    parser.add_argument("--modifier", action="append", default=[],
                        help="modificateur actif, ex: mobDamageMul:150 ou nightMode (répétable)")
    parser.add_argument("--list", action="store_true", help="liste les missions et modificateurs")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    missions = load("missions.json")
    modes = load("difficulty_modes.json")
    mods = load("modifier_multipliers.json")

    if args.selftest:
        selftest()
        return
    if args.list:
        print("Missions :", ", ".join(missions["missions"]))
        print("Modificateurs :")
        for key, cfg in mods["modifiers"].items():
            sens = "aide le joueur" if cfg.get("beneficial") else "durcit le niveau"
            print(f"  {key:<22} x{cfg['multiplier']:<5} ({sens})")
        return
    if not args.mission:
        parser.error("--mission est requis (ou --list / --selftest)")

    try:
        result = evaluate(missions, modes, mods, args.mission, args.mode,
                          threat=args.threat, modifiers=args.modifier)
    except (KeyError, ValueError) as exc:
        sys.exit(f"Erreur : {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

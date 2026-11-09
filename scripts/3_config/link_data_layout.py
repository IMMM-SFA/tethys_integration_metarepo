#!/usr/bin/env python3
"""Build the structured data/ layout Tethys configs expect, as symlinks.

Input data arrives flat, one directory per scenario:

    data/historical/{states.tif,database_*,output_wo_harvforest_*.nc,...}

Tethys reads it by category instead. This script creates the category tree
as relative symlinks, so no file is copied and the delivered layout stays
untouched.

A second, already-structured tree can be merged in with --fallback. On
deception /rcfs/projects/im3/tethys/input holds 43G in exactly this layout
covering all nine scenarios, so the repo only needs to carry what that tree
lacks. Sources merge per destination filename and the flat scenario dir
wins, so a category can draw from both: the repo supplies the annual
demeter years, the fallback the five-yearly ones.

    python scripts/3_config/link_data_layout.py            # all scenarios found
    python scripts/3_config/link_data_layout.py --dry-run
    python scripts/3_config/link_data_layout.py --fallback /rcfs/projects/im3/tethys/input

With no --fallback the value of `structured_input` for $TETHYS_ENV in
scripts/3_config/paths.yml is used when it names a readable directory.

Idempotent: symlinks it owns are replaced, real files are never touched.
Categories with no source in either tree are reported, not silently skipped.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCENARIOS = ["historical"] + [
    f"rcp{r}{t}_ssp{s}" for r in (45, 85) for t in ("cooler", "hotter") for s in (3, 5)
]

# (destination subdir, source glob, subdir to use inside --fallback)
#
# The glob runs against each flat scenario dir and against
# <fallback>/<fallback_subdir>. The third field is needed where the two
# layouts disagree: the fallback keeps the demeter NetCDFs one level down in
# demeter_78_PFT_output/, with only filter.yml beside it.
#
# No rule aliases a filename: run_scenario.py reads
# updated_irrigation_weight_*, which is a genuinely different and newer file
# than irrigation_weight_* (287,238,737 vs 257,727,820 bytes for rcp45cooler).
# Aliasing would feed the stale weights under the current name, silently.
RULES = [
    ("maps", "{states,statebasins,USA,USAbasins}.tif", "maps"),
    ("gcam", "database_*", "gcam"),
    ("demeter", "output_wo_harvforest_*.nc", "demeter/demeter_78_PFT_output"),
    ("demeter/demeter_78_PFT_output", "output_wo_harvforest_*.nc",
     "demeter/demeter_78_PFT_output"),
    ("livestock", "5_*_Da.tif", "livestock"),
    ("population", "ssp[0-9]_[0-9][0-9][0-9][0-9].tif", "population"),
    ("powerplants", "*gppd_im3_tethys_plants.nc", "powerplants"),
    ("monthly", "DomesticR.nc", "monthly"),
    ("monthly/Tavg_HDD_CDD", "Tavg_HDD_CDD_*.nc", "monthly/Tavg_HDD_CDD"),
    ("monthly/deficit", "*irrigation_weight_*.nc", "monthly/deficit"),
]

# Categories shared across scenarios rather than carrying a scenario label.
# Linking them from more than one scenario would collide, so the first
# scenario that supplies them wins.
SHARED = {"maps", "livestock", "monthly", "monthly/Tavg_HDD_CDD"}


def expand(glob: str, root: Path) -> list[Path]:
    """Resolve a glob, including the {a,b} brace form that pathlib lacks."""

    if not root.is_dir():
        return []
    if "{" not in glob:
        return sorted(root.glob(glob))

    head, rest = glob.split("{", 1)
    body, tail = rest.split("}", 1)
    out: list[Path] = []
    for choice in body.split(","):
        out.extend(expand(f"{head}{choice}{tail}", root))
    return sorted(set(out))


def link(src: Path, dest: Path, dry_run: bool) -> str:
    """Point dest at src with a relative symlink. Returns a status word."""

    if dest.is_symlink():
        if dest.resolve() == src.resolve():
            return "ok"
        if dry_run:
            return "relink"
        dest.unlink()
    elif dest.exists():
        return "blocked"

    if dry_run:
        return "create"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(os.path.relpath(src, dest.parent))
    return "create"


def default_fallback(script_dir: Path) -> Path | None:
    """structured_input for $TETHYS_ENV from paths.yml, if it resolves."""

    try:
        import yaml
    except ImportError:
        return None
    try:
        cfg = yaml.safe_load((script_dir / "paths.yml").read_text())
        env = os.environ.get("TETHYS_ENV", "local")
        value = cfg["environments"][env].get("structured_input")
    except (OSError, KeyError, TypeError):
        return None
    if value and Path(value).is_dir():
        return Path(value)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--scenario", action="append", help="repeatable; default all")
    ap.add_argument("--fallback", type=Path,
                    help="already-structured tree merged in behind the flat dirs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = args.data_dir
    if not data.is_dir():
        print(f"error: {data} is not a directory (run from the repo root)", file=sys.stderr)
        return 1

    fallback = args.fallback or default_fallback(Path(__file__).resolve().parent)
    if fallback and not fallback.is_dir():
        print(f"error: --fallback is not a directory: {fallback}", file=sys.stderr)
        return 1

    wanted = args.scenario or SCENARIOS
    present = [s for s in wanted if (data / s).is_dir()]
    if not present and not fallback:
        print(f"error: none of {wanted} found under {data}/", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    claimed: set[str] = set()
    missing: list[str] = []
    blocked: list[Path] = []
    from_fallback = 0

    for subdir, glob, fb_subdir in RULES:
        if subdir in SHARED and subdir in claimed:
            continue

        # Drop symlinks whose target has gone, so a source removed upstream
        # does not leave a dangling link behind.
        dest_dir = data / subdir
        if dest_dir.is_dir():
            for existing in dest_dir.iterdir():
                if existing.is_symlink() and not existing.exists():
                    if args.dry_run:
                        counts["prune"] = counts.get("prune", 0) + 1
                    else:
                        existing.unlink()
                        counts["pruned"] = counts.get("pruned", 0) + 1

        # Merge per destination filename; the flat scenario dir wins.
        chosen: dict[str, Path] = {}
        for scenario in present:
            for src in expand(glob, data / scenario):
                chosen.setdefault(src.name, src)
        flat_names = set(chosen)
        if fallback:
            for src in expand(glob, fallback / fb_subdir):
                chosen.setdefault(src.name, src)

        if not chosen:
            missing.append(f"{subdir} <- {glob}")
            continue
        if subdir in SHARED:
            claimed.add(subdir)

        for name, src in sorted(chosen.items()):
            status = link(src, data / subdir / name, args.dry_run)
            counts[status] = counts.get(status, 0) + 1
            if name not in flat_names:
                from_fallback += 1
            if status == "blocked":
                blocked.append(data / subdir / name)

    verb = "would link" if args.dry_run else "linked"
    summary = ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) or "nothing"
    print(f"{verb}: {summary}  (scenarios: {', '.join(present) or 'none'})")
    if fallback:
        print(f"fallback: {fallback}  ({from_fallback} links drawn from it)")

    if missing:
        print(f"\nno source files for {len(missing)} categories:")
        for m in missing:
            print(f"  {m}")

    if blocked:
        print(f"\nrefused to replace {len(blocked)} real files:", file=sys.stderr)
        for b in blocked:
            print(f"  {b}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

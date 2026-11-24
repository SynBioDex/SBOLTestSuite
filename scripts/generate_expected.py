"""Generate the SBOLTestSuite reference data under Expected/, Rules/, and Ontology/.

Expected/validation/issues.json
    For every SBOL 2 file (SBOL2, SBOL2_bp, SBOL2_ic, SBOL2_nc, InvalidFiles) and every SBOL 3 file (SBOL3,
    SBOL3_InvalidFiles), the validation issues a conforming validator reports under each configuration in
    CONFIGS, as [rule, severity, subject, [configurations]]. Blank-node subjects are written as "_:".

Expected/conversion/
    For every SBOL 2 file: its SBOL 3 upgrade (<path>.upgrade.ttl) and, when upgrading the downgrade of that
    upgrade does not reproduce it, the result of that round trip (<path>.roundtrip.ttl). For every SBOL 3 file:
    its SBOL 2 downgrade (<path>.downgrade.xml) and the upgrade of that downgrade (<path>.roundtrip.ttl).
    index.json lists each file's outputs. sbolconverter/ holds outputs of the SynBioDex/SBOL-Converter reference
    implementation for a few inputs (see --sbolconverter-image).

Rules/
    The SBOL 2.3.0 and SBOL 3.1.0 validation-rule catalogs as JSON.

Ontology/
    The ontology facts snapshot validators use for ontology-dependent rules (term labels omitted).

The validation issues, conversions, rule catalogs, and ontology facts are produced with sbol-rs
(https://github.com/SynBioDex/sbol-rs): pass its `sbol` CLI binary and a checkout of its source. Relative IRIs
resolve against http://sbols.org/unspecified/.

Usage:
    python3 scripts/generate_expected.py --sbol-cli /path/to/sbol --sbol-rs /path/to/sbol-rs \
        [--sbolconverter-image sbolconverter-pinned]
Requires Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = ROOT / "Expected"
SBOL2_DIRS = ("SBOL2", "SBOL2_bp", "SBOL2_ic", "SBOL2_nc", "InvalidFiles")
SBOL3_DIRS = ("SBOL3", "SBOL3_InvalidFiles")
CONVERSION_SBOL2_DIRS = ("SBOL2", "SBOL2_bp", "SBOL2_ic", "SBOL2_nc")
CONVERSION_SBOL3_DIRS = ("SBOL3",)

#: configuration name -> (CLI flags, gate settings it corresponds to)
CONFIGS = {
    "sbol2": {
        "default": ([], {}),
        "incomplete": (["--incomplete"], {"complete": False}),
        "non_compliant": (["--non-compliant"], {"compliant": False}),
        "best_practice": (["--best-practice"], {"best_practice": True}),
    },
    "sbol3": {
        "default": ([], {}),
        "incomplete": (["--incomplete"], {"complete": False}),
        "non_compliant": (["--non-compliant"], {"compliant": False}),
        "no_best_practices": (["--no-best-practices"], {"best_practice": False}),
    },
}

#: SBOL-Converter reference cases: output stem -> (source, direction)
SBOLCONVERTER_CASES = {
    "component_definition_output": ("SBOL2/ComponentDefinitionOutput.xml", "to-sbol3"),
    "module_definition_output": ("SBOL2/ModuleDefinitionOutput.xml", "to-sbol3"),
    "sequence_constraint_output": ("SBOL2/SequenceConstraintOutput.xml", "to-sbol3"),
    "repression_model": ("SBOL2/RepressionModel.xml", "to-sbol3"),
    "bba_f2620": ("SBOL3/BBa_F2620_PoPSReceiver/BBa_F2620_PoPSReceiver.ttl", "to-sbol2"),
    "model": ("SBOL3/entity/model/model.ttl", "to-sbol2"),
}


def sbol2_files(dirs) -> List[Path]:
    """RDF/XML files of SBOL 2 directories."""
    return sorted(p for d in dirs for p in (ROOT / d).glob("*.xml"))


def sbol3_files(dirs) -> List[Path]:
    """Turtle files of SBOL 3 directories (each SBOL 3 test case also ships other serializations)."""
    return sorted(p for d in dirs for p in (ROOT / d).rglob("*.ttl"))


def rel(path: Path) -> str:
    """Suite-relative POSIX path."""
    return path.relative_to(ROOT).as_posix()


def run(command: List[str]) -> subprocess.CompletedProcess:
    """Run a command, capturing text output."""
    return subprocess.run(command, capture_output=True, text=True)


# --- validation --------------------------------------------------------------------------------------------------


def validation_issues(cli: str, version: str, path: Path, flags: List[str]) -> List[Tuple[str, str, str]]:
    """Distinct (rule, severity, subject) issues for one file and configuration."""
    result = run([cli, "validate", "--format", "json", "--sbol-version", version[-1], *flags, str(path)])
    if not result.stdout.strip():
        message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
        return [("<parse-error>", "Error", message.replace(str(path), path.name))]
    issues = set()
    for issue in json.loads(result.stdout)["issues"]:
        subject = issue.get("subject") or ""
        issues.add((issue["rule"], issue["severity"], "_:" if subject.startswith("_:") else subject))
    return sorted(issues)


def write_validation(cli: str, version_line: str) -> None:
    """Write Expected/validation/issues.json."""
    jobs = [("sbol2", p) for p in sbol2_files(SBOL2_DIRS)] + [("sbol3", p) for p in sbol3_files(SBOL3_DIRS)]
    tasks = [(v, p, name, flags) for v, p in jobs for name, (flags, _) in CONFIGS[v].items()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda t: validation_issues(cli, t[0], t[1], t[3]), tasks))
    merged: Dict[str, Dict[tuple, List[str]]] = {}
    versions: Dict[str, str] = {}
    for (version, path, name, _), issues in zip(tasks, results):
        versions[rel(path)] = version
        for issue in issues:
            merged.setdefault(rel(path), {}).setdefault(issue, []).append(name)
        merged.setdefault(rel(path), {})
    header = {
        "description": "Expected validation issues per file and configuration: [rule, severity, subject, [configs]]",
        "generator": f"scripts/generate_expected.py with {version_line}",
        "base_iri": "http://sbols.org/unspecified/",
        "configs": {v: {name: cfg[1] for name, cfg in configs.items()} for v, configs in CONFIGS.items()},
    }
    lines = ["{"] + [f" {json.dumps(k)}: {json.dumps(v, sort_keys=True)}," for k, v in header.items()]
    lines.append(' "files": {')
    entries = []
    for key in sorted(merged):
        issues = [[*issue, sorted(cfgs)] for issue, cfgs in sorted(merged[key].items())]
        entries.append(f"  {json.dumps(key)}: {json.dumps({'version': versions[key], 'issues': issues})}")
    lines += [",\n".join(entries), " }", "}"]
    out = EXPECTED / "validation" / "issues.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(merged)} files -> {rel(out)}")


# --- conversion --------------------------------------------------------------------------------------------------


def convert(cli: str, command: str, source: Path, target: Path) -> Optional[str]:
    """Run one conversion; return an error message, or None on success."""
    result = run([cli, command, str(source), "-o", str(target)])
    if result.returncode == 0 and target.exists():
        return None
    return (result.stderr.strip().splitlines() or ["conversion failed"])[-1].replace(str(source), source.name)


def triple_set(cli: str, path: Path) -> set:
    """N-Triples lines of an SBOL 3 file (blank-node labels masked), for fixed-point detection."""
    text = run([cli, "convert", str(path), "--to", "ntriples"]).stdout
    return {re.sub(r"_:\S+", "_:", line) for line in text.splitlines() if line.strip()}


def conversion_entry(cli: str, path: Path, version: str) -> Tuple[str, Dict[str, str]]:
    """Write the expected outputs for one file and return its index entry."""
    base = EXPECTED / "conversion" / rel(path)
    base.parent.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, str] = {}
    if version == "sbol2":
        upgraded = base.with_name(base.name + ".upgrade.ttl")
        error = convert(cli, "upgrade", path, upgraded)
        if error:
            return rel(path), {"upgrade": f"error: {error}"}
        entry["upgrade"] = rel(upgraded)
        with tempfile.TemporaryDirectory() as tmp:
            down, again = Path(tmp) / "down.xml", Path(tmp) / "again.ttl"
            error = convert(cli, "downgrade", upgraded, down) or convert(cli, "upgrade", down, again)
            if error:
                entry["roundtrip"] = f"error: {error}"
            elif triple_set(cli, again) == triple_set(cli, upgraded):
                entry["roundtrip"] = "fixed-point"
            else:
                target = base.with_name(base.name + ".roundtrip.ttl")
                target.write_bytes(again.read_bytes())
                entry["roundtrip"] = rel(target)
    else:
        downgraded = base.with_name(base.name + ".downgrade.xml")
        error = convert(cli, "downgrade", path, downgraded)
        if error:
            return rel(path), {"downgrade": f"error: {error}"}
        entry["downgrade"] = rel(downgraded)
        again = base.with_name(base.name + ".roundtrip.ttl")
        error = convert(cli, "upgrade", downgraded, again)
        entry["roundtrip"] = f"error: {error}" if error else rel(again)
    return rel(path), entry


def write_conversion(cli: str, version_line: str) -> None:
    """Write Expected/conversion/ and its index."""
    jobs = [(p, "sbol2") for p in sbol2_files(CONVERSION_SBOL2_DIRS)]
    jobs += [(p, "sbol3") for p in sbol3_files(CONVERSION_SBOL3_DIRS)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = dict(pool.map(lambda j: conversion_entry(cli, *j), jobs))
    index = {
        "description": "Expected SBOL 2 <-> SBOL 3 conversion outputs; paths are relative to the suite root",
        "generator": f"scripts/generate_expected.py with {version_line}",
        "base_iri": "http://sbols.org/unspecified/",
        "files": dict(sorted(entries.items())),
    }
    out = EXPECTED / "conversion" / "index.json"
    out.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    print(f"{len(entries)} files -> {rel(out)}")


def write_sbolconverter(image: str) -> None:
    """Regenerate Expected/conversion/sbolconverter/ with the pinned SBOL-Converter Docker image."""
    out_dir = EXPECTED / "conversion" / "sbolconverter"
    for stem, (source, direction) in SBOLCONVERTER_CASES.items():
        suffix = "to-sbol3.nt" if direction == "to-sbol3" else "to-sbol2.rdf"
        command = ["docker", "run", "--rm", "-v", f"{ROOT}:/suite:ro", image, f"/suite/{source}", direction, "nt"]
        result = run(command)
        if result.returncode != 0:
            raise SystemExit(f"SBOL-Converter failed on {source}: {result.stderr}")
        (out_dir / f"{stem}.sbolconverter.{suffix}").write_text(result.stdout, encoding="utf-8")
    print(f"{len(SBOLCONVERTER_CASES)} SBOL-Converter outputs -> {rel(out_dir)}")


# --- rule catalogs and ontology -------------------------------------------------------------------------------------


def write_rules_and_ontology(sbol_rs: Path, revision: str) -> None:
    """Write Rules/*.json and Ontology/*.tsv from an sbol-rs checkout."""
    rules_dir = ROOT / "Rules"
    rules_dir.mkdir(exist_ok=True)
    for version in ("2", "3"):
        with open(sbol_rs / "crates" / f"sbol{version}" / "rules.toml", "rb") as handle:
            catalog = tomllib.load(handle)
        catalog["meta"]["source"] = f"sbol-rs@{revision}"
        out = rules_dir / f"sbol{version}-rules.json"
        out.write_text(json.dumps(catalog, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{len(catalog['rule'])} rules -> {rel(out)}")
    ontology_dir = ROOT / "Ontology"
    ontology_dir.mkdir(exist_ok=True)
    source = sbol_rs / "crates" / "sbol-ontology" / "data"
    lines = []
    for line in (source / "sbol3_ontology_facts.tsv").read_text(encoding="utf-8").splitlines():
        if line.startswith("term\t"):
            columns = line.split("\t")
            columns[3] = "-"  # labels are not needed for validation
            line = "\t".join(columns)
        lines.append(line)
    (ontology_dir / "ontology_facts.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ontology_dir / "ontology_sources.tsv").write_text(
        (source / "ontology_sources.tsv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"ontology facts -> {rel(ontology_dir)}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sbol-cli", required=True, help="sbol-rs `sbol` binary")
    parser.add_argument("--sbol-rs", required=True, type=Path, help="sbol-rs source checkout")
    parser.add_argument("--sbolconverter-image", help="Docker image of the pinned SBOL-Converter (optional)")
    args = parser.parse_args()
    version_line = run([args.sbol_cli, "--version"]).stdout.strip()
    revision = run(["git", "-C", str(args.sbol_rs), "rev-parse", "HEAD"]).stdout.strip()
    write_rules_and_ontology(args.sbol_rs.expanduser(), revision)
    write_validation(args.sbol_cli, version_line)
    write_conversion(args.sbol_cli, version_line)
    if args.sbolconverter_image:
        write_sbolconverter(args.sbolconverter_image)


if __name__ == "__main__":
    main()

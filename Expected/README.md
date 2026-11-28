# Expected outputs

Reference results for the SBOLTestSuite files, for implementations to compare against. All of it is produced by
`scripts/generate_expected.py`; regenerate it after adding or changing a test file.

## Conventions

- Paths are relative to the suite root.
- Relative IRIs in a test file resolve against `http://sbols.org/unspecified/`.
- Inputs are read as their format specifies: XML line ends are normalized (XML 1.0, section 2.11), and an RDF graph
  holds each distinct triple once.
- Graphs are compared as RDF graphs (blank nodes up to isomorphism), not as text.

## `validation/issues.json`

For each SBOL2 file (SBOL2, SBOL2_bp, SBOL2_ic, SBOL2_nc, InvalidFiles) and each SBOL3 file (SBOL3,
SBOL3_InvalidFiles): every distinct issue as `[rule, severity, subject, [configurations]]`, where the
configurations are those under which the issue is reported. `configs` defines each configuration as the rule
families it switches relative to the defaults: completeness and compliant-URI rules on for both versions,
best-practice (SHOULD) rules on for SBOL3 and off for SBOL2. A subject that is a blank node is written `_:`. A file
whose RDF cannot be read has the single issue `<parse-error>`.

## `conversion/`

`index.json` lists, for each file:

- SBOL2 files: `upgrade`, the SBOL3 conversion (`<path>.upgrade.ttl`), and `roundtrip`: `fixed-point` when
  converting that SBOL3 back to SBOL2 and up again reproduces it, otherwise the result of doing so
  (`<path>.roundtrip.ttl`).
- SBOL3 files: `downgrade`, the SBOL2 conversion (`<path>.downgrade.xml`), and `roundtrip`, the SBOL3 conversion
  of that SBOL2 (`<path>.roundtrip.ttl`). SBOL2 cannot represent everything SBOL3 can (for example a feature's own
  orientation), so this round trip need not reproduce the input.

Conversions follow the SynBioDex/SBOL-Converter reference (identities, class choices, vocabulary, and
`https://sbols.org/backport/2_3#` annotations), except that only identifiers.org ontology terms are respelled
between the SBOL2 and SBOL3 conventions; other role and type IRIs are kept exactly as written.

`sbolconverter/` holds the SBOL-Converter's own output for six inputs, with the Docker image (`Dockerfile`,
`Convert.java`) that reproduces it. Comparing against it, ignore the http/https scheme of role and type IRIs that
are not identifiers.org terms: the SBOL-Converter changes their scheme.

## Provenance

The validation issues, conversions, rule catalogs (`../Rules/`), and ontology facts (`../Ontology/`) were produced
with sbol-rs (https://github.com/SynBioDex/sbol-rs); the exact version is recorded in each file's `generator` or
`source` field. The ontology facts are derived from EDAM, SBO, SO, GO, ChEBI, and the Cell Ontology, whose
versions and licenses are listed in `../Ontology/ontology_sources.tsv`.

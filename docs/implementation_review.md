# Implementation review and nf-core alignment

Reviewed against the [nf-core specifications](https://nf-co.re/docs/specifications/overview), including [module conventions](https://nf-co.re/docs/guidelines/components/modules) and [subworkflow conventions](https://nf-co.re/docs/guidelines/components/subworkflows).

## Changes made during review

- Removed unreachable project-folder expansion from the integrated workflow. The existing explicit project-mode rejection remains; sample pairing is now easier to read.
- Added `task.ext.when` guards to the new RAMI2D processes and exporter.
- Added missing version-topic outputs for RAMI2D result packaging and the NGFF exporter. The pipeline already collects version topics for MultiQC.
- Replaced template README badges, unavailable upstream commands and unsupported project-mode instructions with this fork's actual setup and entry point.
- Kept registration algorithms, transform mathematics and image processing unchanged.

## Deliberate local conventions and remaining work

These are pipeline-local components, not components ready for submission to nf-core/modules. Do not describe this development fork as fully nf-core compliant.

- Containers currently require local Docker builds. Publish immutable, multi-platform images and lock transitive dependencies before a portable release. Other engines have not been validated in this prototype.
- Add component `meta.yml` descriptions and dedicated nf-test cases/snapshots before upstream component submission. Current Python, full-workflow stub and Docker integration tests are documented in `tests/prototype/README.md`; they do not replace every nf-core component check.
- The new RAMI2D wrapper passes a validated settings value with its staged files so calibration, chosen channels and provenance stay together. Optional CLI settings are not yet exposed through the standard `task.ext.args` convention. A future interface change must ensure argument overrides cannot make the recorded settings disagree with the command actually run.
- Pipeline-specific Python helpers live in `bin/`. Extract reusable modules and module-local templates only if preparing them for independent distribution.
- The exporter wrapper contains one process. It remains a named pipeline boundary matching the metro map, rather than a reusable multi-module subworkflow for upstream submission.
- Existing template-derived modules and unrelated legacy interfaces have not been rewritten. Version topics are retained consistently with the current pipeline template rather than introducing parallel `versions.yml` aggregation.
- Full acquisition processing, full-size segmentation, nonlinear transforms and spatial-omics inputs still need their own validation. The toy data are derived from local imaging data and are not committed as public test fixtures.

## Validation

Run the adapter unit tests, `nextflow lint`, and the four full-workflow stub combinations as described in the test documentation. The scientific Docker validation and RFC-5/Transformix comparisons from the implementation milestone remain applicable because this cleanup changes orchestration guards, version reporting and documentation only.

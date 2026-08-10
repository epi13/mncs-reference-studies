# MNCS case studies

This directory is the migration target for bounded research case studies currently stored in `epi13/machine-native-complexity-standard/case-studies`.

These studies predate the MRS reference-reimplementation series and should retain their own experimental identities. Migration should not rewrite their conclusions merely to fit the newer MRS template.

## Source inventory

As of the repository bootstrap, the core MNCS repository contains:

| Source directory | Study | Migration status |
|---|---|---|
| `cacheforge/` | CacheForge | PENDING |
| `composed-gateway/` | Composed Gateway | PENDING |
| `dsense-desk-pet/` | dSense Desk Pet | PENDING |
| `edgestream/` | EdgeStream | PENDING |
| `edgestream-remote-water-integration/` | EdgeStream Remote Water Integration | PENDING |
| `go-gateway/` | Go Gateway | PENDING |
| `multilingual-stream/` | Multilingual Stream | PENDING |
| `ravel/` | RAVEL | PENDING |
| `remote-water-control/` | Remote Water Control | PENDING |

The source repository explicitly warns that favorable development results are not automatically formal MNCS or MNCDS claims. Preserve that boundary during migration.

## Migration rules

For each migration:

1. record the source repository and source commit SHA;
2. preserve study-local README, contracts, preregistration, tests, evidence, and claim language;
3. identify workflows or root Makefile targets that must be adapted after the move;
4. avoid silently regenerating evidence during the migration itself;
5. run study-local validation after paths are repaired;
6. add a `MIGRATION.md` recording material path/build changes;
7. only then update/remove the corresponding content in the standards repository.

See [`../methodology/migration.md`](../methodology/migration.md).

# Cross-study regression tests

These tests preserve historical validation that used to be located in the standards
repository. They remain empirical tests and are not part of the default normative
validator check.

Most tests need the standards repository for normative schemas and the `mncs_validator`
package. Run them with an explicit frozen checkout:

```bash
MNCS_STANDARDS_ROOT=/path/to/machine-native-complexity-standard \
  PYTHONPATH=/path/to/machine-native-complexity-standard/src \
  pytest tests
```

The default repository check runs the study-local, evidence-preserving checks through
the root `GNUmakefile`. It does not regenerate frozen evidence.

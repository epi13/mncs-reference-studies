# Rollback

Build and select `build/reference-gcc` or `build/reference-clang` instead of the generated
candidate. Checkpoint representation is shared, so a valid candidate checkpoint can be
restored by the reference implementation under the same contract and environment.

Run `python tools/run_study.py test` before switching and preserve the manifest and
evidence identities associated with the retired candidate.

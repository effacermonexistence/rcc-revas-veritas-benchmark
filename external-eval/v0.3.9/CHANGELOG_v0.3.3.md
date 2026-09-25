# 0.3.3

- Add native-job/v1, a source-pinned whole-native-loop execute/score backend
  using existing freeze/run/verify/matrix commands, with exact enrollment and
  immutable execution artifacts before native scoring.
- Bind lm-eval native call options before review and reject later mutation.
- Execute exactly the pinned invocation path (including Python venv identity).
- Add source-linked 12-group VERITAS field mapping, original Q1-Q9 answers,
  typed packet builder/verifier, JSON Schemas and English/Japanese runbooks.
- Separate benchmark-fitness records from executable compatibility; historical
  known-gold SWE setup evidence is not model quality or universality evidence.
- Add 33 regression cases; all 299 core/native integration tests pass on declared
  pinned native sources. Preserve past artifacts and failed setup attempts.

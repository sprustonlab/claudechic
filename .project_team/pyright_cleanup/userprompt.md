# User Prompt

> I want to know if we should invest in fixing all the pyright issues.

After investigation (307 errors across 37 files; pre-commit currently broken; 68% of errors in tests), the user chose **Level B** investment:

> Fix all non-test pyright errors AND triage / fix genuine bugs surfaced by pyright in the test suite. Mechanical test errors may be excluded or relaxed via config.

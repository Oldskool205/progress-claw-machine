# Contributing

## Code Style

- Keep module-specific behavior inside that module.
- Put shared code in `claw-core` only when at least two modules need it.
- Prefer small services with explicit dependencies.

## Checks

Run the build before submitting changes:

```sh
gradle build
```

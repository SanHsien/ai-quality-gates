# AI Quality Gates

[繁體中文](README.md)

An executable Python reference for constraining AI-assisted development with specifications, automated tests, and measurable engineering gates.

The repository implements unit and integration tests, Gherkin acceptance tests, a command-boundary QA smoke, branch coverage, mutation testing, cyclomatic complexity, module-size limits, dependency contracts, static analysis, supply-chain checks, and GitHub CI. It does not claim that metrics prove correctness.

## Quick start

Windows:

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
pwsh -NoProfile -File tools\dev_check.ps1 -Quick
pwsh -NoProfile -File tools\dev_check.ps1
```

Linux or WSL:

```bash
bash tools/bootstrap_dev.sh
bash tools/dev_check.sh
bash tools/mutation_check.sh
```

The full gate writes machine-readable evidence to `artifacts/`. See the [quality gate rationale](docs/quality-gates.md), [article research](docs/article-notes.md), and [architecture](docs/architecture.md).

## License

[MIT](LICENSE)

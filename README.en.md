# AI Quality Gates

[繁體中文](README.md)

An executable Python reference for constraining AI-assisted development with specifications, automated tests, measurable engineering gates, and bounded agent loops.

The repository implements unit and integration tests, Gherkin acceptance tests, a command-boundary QA smoke, branch coverage, mutation testing, cyclomatic complexity, module-size limits, dependency contracts, static analysis, supply-chain checks, and GitHub CI. A fail-closed `loop-policy.toml` adds iteration, time, token, isolation, independent-verifier, human-approval, and stopping constraints. It does not claim that metrics prove correctness.

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

The full gate writes machine-readable evidence to `artifacts/`. See the [engineering principles](docs/engineering-principles.md), [quality gate rationale](docs/quality-gates.md), [bounded Loop Engineering policy](docs/loop-engineering.md), and [architecture](docs/architecture.md).

## Related tools

These four repositories each govern a different layer of AI coding. Use one on its own, or stack them:

| Layer | Repo | What it does |
| --- | --- | --- |
| Dispatch decision | [agent-advisor](https://github.com/SanHsien/agent-advisor) | Risk-gated routing -- `solo`, `delegate`, `audit`, `full`: whether to delegate at all, and to whom |
| Action interception | [harness-guard](https://github.com/SanHsien/harness-guard) | Agent runtime hooks that actually block dangerous commands, unevidenced claims, and commits over red tests |
| Output quality | **AI Quality Gates (you are here)** | Executable specs and quantified thresholds: coverage, mutation, cyclomatic complexity, dependency structure, bounded loop policy |
| Delivery lifecycle | [paulsha-cortex](https://github.com/SanHsien/paulsha-cortex) | Multi-agent lifecycle: Candidate -> Verify -> Independent Review -> Delivery -> CompletionRecord |

Adjacent but a different layer: [opencodex](https://github.com/SanHsien/opencodex) is a provider proxy that decides which LLMs these agents can run on. It does not constrain agent behaviour.

## License

[MIT](LICENSE)

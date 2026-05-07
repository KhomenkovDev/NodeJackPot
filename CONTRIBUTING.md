# Contributing to NodeJackPot

Thank you for your interest in contributing to NodeJackPot! 🐍⚔️

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/khomev/NodeJackPot.git
   cd NodeJackPot
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Compile contracts**
   ```bash
   mox compile
   ```

4. **Run tests**
   ```bash
   mox test -v
   ```

## Code Standards

- **Vyper contracts** follow [Vyper 0.4.x conventions](https://docs.vyperlang.org/en/stable/style-guide.html)
- `@nonreentrant` is used without parentheses (Vyper 0.4.x syntax)
- All state-mutating functions must emit events
- Every revert path requires a corresponding unit test
- NatSpec-style docstrings on all externals

## Pull Request Guidelines

1. Fork the repo and create a feature branch from `main`
2. Write tests for any new functionality
3. Ensure `mox test -v` passes with zero failures
4. Run the stateful fuzzer: `mox test tests/unit/test_stateful_fuzzer.py -s`
5. Keep commits atomic and well-described

## Reporting Issues

Please use the GitHub issue tracker with a descriptive title and steps to reproduce.

---

Thank you for helping make NodeJackPot more robust! ⚔️

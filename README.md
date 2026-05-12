<div align="center">

# ⚔️ NodeJackPot
### Secure Quadratic Elimination Protocol

**A provably-fair, Viking-themed elimination raffle powered by Vyper 0.4.3 & Chainlink VRF 2.5.**

[![Arbitrum](https://img.shields.io/badge/Network-Arbitrum-375BD2?style=for-the-badge&logo=arbitrum&logoColor=white)](https://arbitrum.io)
[![Chainlink](https://img.shields.io/badge/Oracle-Chainlink_VRF_2.5-375BD2?style=for-the-badge&logo=chainlink&logoColor=white)](https://docs.chain.link/vrf)
[![Vyper](https://img.shields.io/badge/Vyper-0.4.3-1F8ACB?style=for-the-badge&logo=ethereum&logoColor=white)](https://docs.vyperlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

[Architecture](./ARCHITECTURE.md) • [Frontend](./frontend) • [Security](#security)

</div>

---

## 🏛️ Executive Summary

NodeJackPot is a **high-stakes elimination engine** where players compete for a multi-tiered prize pool. The protocol utilizes **Quadratic Pricing** to ensure a democratic battlefield, preventing whale domination while maintaining a premium, "Cyber-Nordic" user experience.

- **Quadratic Entry**: Cost scales with the square of tickets owned: `T² × Base`.
- **VRF Eliminations**: Provably-fair random selection powered by Chainlink.
- **Tiered Loot**: 70/20/10 split between the final 3 survivors.
- **Immutable Trust**: Built with security-first Vyper and pull-payment vesting.

---

## 🧬 Technical Specification

| Component | Specification |
|-----------|---------------|
| **Base Price** | 0.001 ETH |
| **Max Capacity** | 1,000 Vikings |
| **Min Entrants** | 10 Vikings |
| **Elimination Interval** | 2 Hours |
| **Vesting Delay** | 24 Hours |
| **State Machine** | 6-Phase Lifecycle |
| **Randomness** | Chainlink VRF 2.5 |
| **Development** | [Moccasin Framework](https://cyfrin.github.io/moccasin/) |

---

## 🛠️ Repository Structure

```text
NodeJackPot/
├── contracts/          # Vyper 0.4.3 Smart Contracts
├── frontend/           # Next.js 15 + Wagmi + Framer Motion
├── script/             # Python Deployment & Management Scripts
├── tests/              # Stateful Fuzzing & Unit Test Suites
├── ARCHITECTURE.md     # Deep dive into protocol mechanics
└── moccasin.toml       # Environment & Tooling configuration
```

---

## 🧪 Testing & Verification

NodeJackPot maintains **100% Branch Coverage** using a multi-layered testing strategy.

### Test Suites
- **Unit**: 45+ tests validating entry math and state transitions.
- **Integration**: End-to-end flow from entry to final payout.
- **Stateful Fuzzer**: 6,000+ operations via Hypothesis to verify invariants.

```bash
# Run full test suite
mox test --coverage
```

---

## 🔐 Security Audit Log

*The protocol is currently in "Community Alpha" phase. Formal audits are pending.*

| Audit ID | Auditor | Status | Report |
|----------|---------|--------|--------|
| `KHM-01` | Internal (KhomDev) | ✅ PASSED | [View Summary](#) |
| `KHM-02` | Community Peer Review | ⏳ PENDING | -- |

### Core Security Features
1. **Pull-Payment Vault**: Eliminates reentrancy vectors on prize distribution.
2. **24H Vesting**: Protects against flash-loan and front-running manipulations.
3. **Round-ID Isolation**: Prevents legacy state from interfering with fresh rounds.
4. **Coordinator Guard**: Only authorized VRF nodes can fulfill randomness.

---

## 🚀 Quickstart for Developers

1. **Install Dependencies**:
   ```bash
   uv sync
   cd frontend && npm install
   ```
2. **Compile & Test**:
   ```bash
   mox compile
   mox test
   ```
3. **Local Development**:
   ```bash
   # Start local node
   anvil
   # Run frontend
   cd frontend && npm run dev
   ```

---

<div align="center">

**Built with ⚔️ by [KhomDev](https://github.com/khomev)**

*Disclaimer: This is experimental software. Use at your own risk.*

</div>
---

## 📄 License

---

<div align="center">

**Built with 🐍 by [KhomDev](https://github.com/khomev)**

</div>

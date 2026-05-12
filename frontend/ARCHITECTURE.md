# NodeJackPot Frontend Architecture

## Tech Stack
- **Framework**: Next.js 15+ (App Router)
- **Web3**: Wagmi + Viem + ConnectKit
- **Styling**: Tailwind CSS 4 + Framer Motion
- **State**: TanStack Query (Real-time contract polling)

## Core Components

### 1. Quadratic Entry Dashboard (`src/components/QuadraticEntry.tsx`)
- Implements the $Cost = (Tickets + 1)^2 \times BasePrice$ logic.
- Visualizes the diminishing returns curve of ticket acquisition.
- Real-time "Effective Weight" calculator using BigInt for contract parity.

### 2. Elimination Engine Feed (`src/components/EliminationFeed.tsx`)
- Listens for `VikingEliminated` and `EliminationRequested` events.
- Features a "Rolling" state when Chainlink VRF is calculating randomness.
- Real-time updates of survivors vs. total participants.

### 3. Secure Earnings Vault (`src/components/VaultUI.tsx`)
- Pull-payment architecture implementation.
- Time-locked vesting countdown for winners.
- Secure withdrawal button with transaction lifecycle management.

### 4. Security & Audit Specs (`src/app/page.tsx`)
- Prominent display of Vyper contract address.
- Detailed breakdown of VRF integration and vault security.

## Custom Hook: `useJackpotData`
- Aggregates multi-call contract reads into a single reactive object.
- Configured for 5-second polling to ensure UI reflects on-chain state accurately.

## Aesthetic Design
- **Theme**: High-contrast Dark Mode (`bg-black`).
- **Typography**: Inter (UI) & JetBrains Mono (Numbers/Code).
- **Accents**: Neon Emerald (`#00ffaa`) for success/active states.
- **Interactions**: Framer Motion for smooth state transitions and loading skeletons.

# NodeJackPot Architecture — Secure Quadratic Elimination Engine

NodeJackPot is a sophisticated Web3 raffle protocol designed with game-theoretic fairness and cryptographic security. This document details the technical lifecycle and core mechanisms of the protocol.

## 1. Protocol Lifecycle (The 6 Phases)

The raffle operates in a strict state-machine lifecycle, ensuring that actions occur only in the correct order.

### Phase 1: Entry Phase
- **State**: `OPEN`
- **Action**: Participants enter the raffle by purchasing tickets.
- **Mechanism**: Tickets are priced quadratically: `Cost = (current_tickets + 1)² × Base_Fee`. This ensures that doubling your winning probability costs four times as much, discouraging "whale" dominance.
- **Storage**: Player data is stored in `player_profiles`. First-time entrants are appended to the `active_vikings` registry.

### Phase 2: Deadline & Minimums
- **State**: `OPEN` (transitioning)
- **Constraint**: The raffle has a `raffle_deadline`. If the `MIN_ENTRANTS` (10) requirement is not met by the deadline, the owner can trigger a **Jackpot Roll** or **Refund Activation**.

### Phase 3: Elimination Engine (VRF)
- **State**: `ELIMINATING` / `CALCULATING`
- **Action**: The owner triggers `request_elimination()`.
- **Mechanism**: The contract calls **Chainlink VRF 2.5**. The coordinator returns a random word which is used to pick a victim from the `active_vikings` array using modulo: `loser_index = random_word % active_vikings.length`.
- **Optimization**: We use a `swap-and-pop` algorithm to remove the loser from the dynamic array in O(1) gas cost.

### Phase 4: Final Stand
- **Trigger**: When `active_vikings.length == 3`.
- **Action**: The contract automatically transitions to `FINISHED`.
- **Payout**: The remaining 3 participants are assigned as winners:
    - 1st Place: 70% of total pool.
    - 2nd Place: 20% of total pool.
    - 3rd Place: 10% of total pool.

### Phase 5: Vesting & Claims
- **State**: `FINISHED`
- **Mechanism**: **Pull-Payment Pattern**. Funds are moved to a virtual vault.
- **Constraint**: A **24-hour Vesting Delay** is enforced. Winners must wait for `block.timestamp >= unlock_time` before calling `claim_prize()`. This protects the protocol against rapid drain exploits.

### Phase 6: Refund Safety-Switch
- **State**: `REFUNDABLE`
- **Trigger**: Activated if `total_players < MIN_ENTRANTS` post-deadline.
- **Action**: Participants can call `request_refund()` to reclaim their exact ETH contribution.

## 2. Cryptographic Randomness (Chainlink VRF 2.5)

NodeJackPot integrates with Chainlink VRF 2.5 to provide provably-fair eliminations.
- **Request**: `requestRandomWords` is called by the owner.
- **Callback**: `fulfillRandomWords` is called exclusively by the `VRF_COORDINATOR`.
- **Security**: The `request_id` is logged for off-chain verification. Modulo bias is negligible given the large range of the random word relative to the player count.

## 3. Gas Optimizations & Storage Packing

- **Immutables**: Global parameters like the `VRF_COORDINATOR` and `ENTRANCE_FEE` are stored as immutables to save 2,100 gas per access.
- **Round-Based Indexing**: Instead of clearing the `player_profiles` mapping (O(n) gas), we use a `round_number`. Profile validity is checked via `player.round_id == round_number`.
- **Swap-and-Pop**: Dynamic array management for survivors ensures that elimination cost remains constant regardless of the number of players.

## 4. Security Controls

| Threat Vector | Mitigation Strategy |
|---------------|---------------------|
| **Reentrancy** | `@nonreentrant` guards on all state-changing functions. |
| **Whale Dominance** | Quadratic pricing makes increasing win probability exponentially expensive. |
| **Randomness Manipulation** | Chainlink VRF 2.5 ensures no single party (including owner) can predict outcomes. |
| **Protocol Drainage** | Pull-payment vault ensures winners can only withdraw their assigned share. |
| **Flash Loan Attacks** | 24-hour vesting delay on claims. |

---
*Built for the Arbitrum Ecosystem by KhomDev*

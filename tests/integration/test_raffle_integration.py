"""
test_raffle_integration.py — Integration Tests for NodeJackPot
===============================================================
End-to-end flows that exercise multiple contract phases together
on a local pyevm backend with the mock VRF coordinator.

These tests verify that phases compose correctly — entry feeds
into elimination, elimination feeds into payout, low-turnout
feeds into refund, and round resets allow re-entry.

Run:
    moccasin test tests/integration/test_raffle_integration.py -v
"""

import pytest
import boa
from contracts.mocks import mock_vrf_coordinator
from eth_utils import to_bytes


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

ELIMINATION_INTERVAL = 7200
VESTING_DELAY = 86400


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def vrf():
    return mock_vrf_coordinator.deploy()


@pytest.fixture
def raffle(vrf):
    from contracts import raffle as rf

    gas_lane = to_bytes(
        hexstr="0x787d74caea10b2b357790d5b5247c2f63d1d91572a9846f780606e4d953677ae"
    )
    return rf.deploy(vrf.address, 0, gas_lane, 500000, 10 ** 15, 30)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _viking(name: str, eth: int = 10 ** 18) -> str:
    addr = boa.env.generate_address(name)
    boa.env.set_balance(addr, eth)
    return addr


def _enter(raffle, players: list):
    """Have each player buy one ticket."""
    fee = raffle.entrance_fee()
    for p in players:
        with boa.env.prank(p):
            raffle.enter_raffle(value=fee)


def _eliminate_one(raffle, vrf, request_id: int):
    """Owner requests + VRF fulfills one elimination."""
    owner = raffle.owner()
    boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
    with boa.env.prank(owner):
        raffle.request_elimination()
    vrf.fulfillRandomWords(request_id, raffle.address)


# ══════════════════════════════════════════════════════════════════════════════
# Integration Test: Full Happy-Path Lifecycle
# ══════════════════════════════════════════════════════════════════════════════


def test_full_lifecycle_entry_to_payout(raffle, vrf):
    """
    OPEN → 5 players enter → eliminate 2 → FINISHED → 3 winners claim.
    Verifies the entire happy-path from entry to payout.
    """
    # 1. Five vikings enter
    vikings = [_viking(f"life_{i}") for i in range(5)]
    _enter(raffle, vikings)
    assert raffle.total_players() == 5
    assert raffle.get_active_count() == 5
    assert raffle.get_pot_size() == 5 * raffle.entrance_fee()

    # 2. First elimination
    _eliminate_one(raffle, vrf, 1)
    assert raffle.get_active_count() == 4
    assert raffle.raffle_state() == 2  # ELIMINATING

    # 3. Second elimination → finishes with 3 survivors
    _eliminate_one(raffle, vrf, 2)
    assert raffle.get_active_count() == 3
    assert raffle.raffle_state() == 8  # FINISHED

    # 4. Verify winners and tiered payouts
    total = raffle.prize_pool()
    assert total > 0
    for i in range(3):
        assert raffle.winners(i) != "0x0000000000000000000000000000000000000000"

    assert raffle.pending_claims(raffle.winners(0)) == (total * 70) // 100
    assert raffle.pending_claims(raffle.winners(1)) == (total * 20) // 100
    assert raffle.pending_claims(raffle.winners(2)) == (total * 10) // 100

    # 5. Wait for vesting and claim all prizes
    boa.env.time_travel(seconds=VESTING_DELAY + 1)
    for i in range(3):
        w = raffle.winners(i)
        expected = raffle.pending_claims(w)
        boa.env.set_balance(w, 0)
        with boa.env.prank(w):
            raffle.claim_prize()
        assert boa.env.get_balance(w) == expected
        assert raffle.pending_claims(w) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Integration Test: Refund Flow
# ══════════════════════════════════════════════════════════════════════════════


def test_refund_flow_low_turnout(raffle, vrf):
    """
    OPEN → 3 players (< MIN_ENTRANTS) → deadline passes →
    activate_refunds → all players get refunded.
    """
    vikings = [_viking(f"refund_{i}") for i in range(3)]
    _enter(raffle, vikings)

    contributions = [raffle.player_profiles(v)[2] for v in vikings]

    # Deadline passes
    boa.env.time_travel(seconds=31)
    owner = raffle.owner()
    with boa.env.prank(owner):
        raffle.activate_refunds()
    assert raffle.raffle_state() == 16  # REFUNDABLE

    # All three refund
    for v, contribution in zip(vikings, contributions):
        boa.env.set_balance(v, 0)
        with boa.env.prank(v):
            raffle.request_refund()
        assert boa.env.get_balance(v) == contribution
        assert raffle.player_profiles(v)[3] is True  # has_refunded


# ══════════════════════════════════════════════════════════════════════════════
# Integration Test: Rolling Jackpot into Next Round
# ══════════════════════════════════════════════════════════════════════════════


def test_rolling_jackpot_carries_to_next_round(raffle, vrf):
    """
    Round 1: 3 players, times out → jackpot rolled → refund → reset.
    Round 2: 4 players enter → eliminate to 3 → prize_pool includes jackpot.
    """
    # Round 1 — low turnout
    r1_vikings = [_viking(f"r1_{i}") for i in range(3)]
    _enter(raffle, r1_vikings)
    pot_r1 = raffle.get_pot_size()

    boa.env.time_travel(seconds=31)
    owner = raffle.owner()
    with boa.env.prank(owner):
        raffle.roll_jackpot()
    assert raffle.next_jackpot() == pot_r1

    # Reset for round 2
    with boa.env.prank(owner):
        raffle.reset_round()
    assert raffle.round_number() == 2
    assert raffle.raffle_state() == 1  # OPEN

    # Round 2 — enough players, eliminate to 3
    r2_vikings = [_viking(f"r2_{i}") for i in range(4)]
    _enter(raffle, r2_vikings)

    _eliminate_one(raffle, vrf, 1)
    assert raffle.raffle_state() == 8  # FINISHED

    # Prize pool = round 2 entries + rolled jackpot from round 1
    assert raffle.prize_pool() >= pot_r1


# ══════════════════════════════════════════════════════════════════════════════
# Integration Test: Multi-Round Reset Cycle
# ══════════════════════════════════════════════════════════════════════════════


def test_multi_round_reset_cycle(raffle, vrf):
    """
    Run two complete rounds back-to-back to verify reset clears state.
    """
    owner = raffle.owner()

    for round_num in range(1, 3):
        vikings = [_viking(f"round{round_num}_{i}") for i in range(4)]
        _enter(raffle, vikings)

        _eliminate_one(raffle, vrf, (round_num - 1) * 1 + 1)
        assert raffle.raffle_state() == 8  # FINISHED
        assert raffle.get_active_count() == 3

        # Reset
        with boa.env.prank(owner):
            raffle.reset_round()

        assert raffle.raffle_state() == 1  # OPEN
        assert raffle.total_players() == 0
        assert raffle.get_active_count() == 0
        assert raffle.round_number() == round_num + 1


# ══════════════════════════════════════════════════════════════════════════════
# Integration Test: Quadratic Re-entry Economics
# ══════════════════════════════════════════════════════════════════════════════


def test_quadratic_pricing_multi_ticket(raffle, vrf):
    """
    One whale buys 3 tickets, three others buy 1 each.
    Verify balance accounting and whale's contribution total.
    """
    whale = _viking("whale", 10 ** 19)
    others = [_viking(f"other_{i}") for i in range(3)]
    fee = raffle.entrance_fee()

    # Whale buys 3 tickets: 1²×fee + 2²×fee + 3²×fee = 14×fee
    with boa.env.prank(whale):
        raffle.enter_raffle(value=fee)       # 1
        raffle.enter_raffle(value=4 * fee)   # 4
        raffle.enter_raffle(value=9 * fee)   # 9

    whale_profile = raffle.player_profiles(whale)
    assert whale_profile[0] == 3  # tickets
    assert whale_profile[2] == 14 * fee  # total contribution

    _enter(raffle, others)

    # 4 unique players total (whale + 3 others)
    assert raffle.total_players() == 4
    # Pot = 14×fee (whale) + 3×fee (others) = 17×fee
    assert raffle.get_pot_size() == 17 * fee

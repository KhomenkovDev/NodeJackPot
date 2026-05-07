"""
test_raffle_staging.py — Staging Tests for NodeJackPot
========================================================
Simulates realistic deployment scenarios on local pyevm that mirror
what would happen on a live testnet (Sepolia / Anvil fork).

These tests deploy contracts directly (bypassing the deploy script's
network config), use realistic player counts, and validate the full
raffle lifecycle as if running on a live network.

Run:
    moccasin test tests/staging/test_raffle_staging.py -v
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
ZERO = "0x0000000000000000000000000000000000000000"
ENTRANCE_FEE = 10 ** 15  # 0.001 ETH — matches moccasin.toml config


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def staged_env():
    """
    Full staging environment: VRF mock + raffle deployed with production-like
    parameters.  Returns (raffle, vrf_mock).
    """
    vrf = mock_vrf_coordinator.deploy()
    from contracts import raffle as rf

    gas_lane = to_bytes(
        hexstr="0x787d74caea10b2b357790d5b5247c2f63d1d91572a9846f780606e4d953677ae"
    )
    raffle = rf.deploy(vrf.address, 0, gas_lane, 500000, ENTRANCE_FEE, 30)
    return raffle, vrf


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _fund_viking(name: str, eth: int = 5 * 10 ** 18) -> str:
    addr = boa.env.generate_address(name)
    boa.env.set_balance(addr, eth)
    return addr


# ══════════════════════════════════════════════════════════════════════════════
# Staging: Deploy Smoke Test
# ══════════════════════════════════════════════════════════════════════════════


def test_deploy_produces_valid_contract(staged_env):
    """The deployed contract has correct initial config."""
    raffle, _ = staged_env
    assert raffle.raffle_state() == 1  # OPEN
    assert raffle.entrance_fee() == ENTRANCE_FEE
    assert raffle.raffle_duration() == 30
    assert raffle.round_number() == 1
    assert raffle.total_players() == 0
    assert raffle.owner() != ZERO


# ══════════════════════════════════════════════════════════════════════════════
# Staging: Realistic 10-Player Full Elimination
# ══════════════════════════════════════════════════════════════════════════════


def test_ten_player_elimination_to_winners(staged_env):
    """
    10 players enter → 7 VRF eliminations → 3 winners → all claim.
    """
    raffle, vrf = staged_env
    owner = raffle.owner()
    fee = raffle.entrance_fee()

    # 1. Ten players enter
    players = []
    for i in range(10):
        p = _fund_viking(f"staging_{i}")
        with boa.env.prank(p):
            raffle.enter_raffle(value=fee)
        players.append(p)

    assert raffle.total_players() == 10
    assert raffle.get_active_count() == 10
    assert raffle.get_pot_size() == 10 * fee

    # 2. Eliminate 7 players one at a time
    for req_id in range(1, 8):
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf.fulfillRandomWords(req_id, raffle.address)

    # 3. FINISHED with 3 survivors
    assert raffle.raffle_state() == 8
    assert raffle.get_active_count() == 3

    # 4. Verify winners
    winners = [raffle.winners(i) for i in range(3)]
    for w in winners:
        assert w != ZERO

    # 5. Verify tiered payouts
    total = raffle.prize_pool()
    assert raffle.pending_claims(winners[0]) == (total * 70) // 100
    assert raffle.pending_claims(winners[1]) == (total * 20) // 100
    assert raffle.pending_claims(winners[2]) == (total * 10) // 100

    # 6. Claim after vesting
    boa.env.time_travel(seconds=VESTING_DELAY + 1)
    for w in winners:
        payout = raffle.pending_claims(w)
        boa.env.set_balance(w, 0)
        with boa.env.prank(w):
            raffle.claim_prize()
        assert boa.env.get_balance(w) == payout


# ══════════════════════════════════════════════════════════════════════════════
# Staging: Full Refund Cycle
# ══════════════════════════════════════════════════════════════════════════════


def test_refund_cycle(staged_env):
    """
    5 players (< MIN_ENTRANTS) → deadline → activate_refunds →
    all refund → reset round.
    """
    raffle, _ = staged_env
    owner = raffle.owner()
    fee = raffle.entrance_fee()

    players = []
    for i in range(5):
        p = _fund_viking(f"refund_stg_{i}")
        with boa.env.prank(p):
            raffle.enter_raffle(value=fee)
        players.append(p)

    # Wait for deadline
    boa.env.time_travel(seconds=31)

    with boa.env.prank(owner):
        raffle.activate_refunds()
    assert raffle.raffle_state() == 16  # REFUNDABLE

    # Everyone refunds
    for p in players:
        contribution = raffle.player_profiles(p)[2]
        boa.env.set_balance(p, 0)
        with boa.env.prank(p):
            raffle.request_refund()
        assert boa.env.get_balance(p) == contribution

    # Reset
    with boa.env.prank(owner):
        raffle.reset_round()
    assert raffle.raffle_state() == 1
    assert raffle.round_number() == 2
    assert raffle.total_players() == 0


# ══════════════════════════════════════════════════════════════════════════════
# Staging: Two Consecutive Full Rounds
# ══════════════════════════════════════════════════════════════════════════════


def test_two_consecutive_rounds(staged_env):
    """
    Two complete rounds back-to-back to verify state is fully reset.
    """
    raffle, vrf = staged_env
    owner = raffle.owner()
    fee = raffle.entrance_fee()

    for round_idx in range(2):
        # Enter 4 players
        players = [_fund_viking(f"r{round_idx}_p{i}") for i in range(4)]
        for p in players:
            with boa.env.prank(p):
                raffle.enter_raffle(value=fee)

        assert raffle.total_players() == 4

        # Eliminate 1 → FINISHED
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf.fulfillRandomWords(round_idx + 1, raffle.address)

        assert raffle.raffle_state() == 8
        assert raffle.get_active_count() == 3

        # Claim all
        boa.env.time_travel(seconds=VESTING_DELAY + 1)
        for i in range(3):
            w = raffle.winners(i)
            if raffle.pending_claims(w) > 0:
                with boa.env.prank(w):
                    raffle.claim_prize()

        # Reset
        with boa.env.prank(owner):
            raffle.reset_round()
        assert raffle.raffle_state() == 1
        assert raffle.round_number() == round_idx + 2
        assert raffle.total_players() == 0

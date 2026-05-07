"""
test_raffle.py — Full-Coverage Unit Tests for NodeJackPot Viking Raffle
========================================================================
Covers all 6 phases: entry & quadratic pricing, VRF elimination engine,
rolling jackpot & tiers, payout & vesting, and refund safety-switch.

Run:
    moccasin test tests/unit/test_raffle.py -v
"""

import pytest
import boa
from script.deploy_raffle import deploy_raffle
from contracts.mocks import mock_vrf_coordinator


# ──────────────────────────────────────────────────────────────────────────────
# Constants (must match the contract)
# ──────────────────────────────────────────────────────────────────────────────

MIN_ENTRANTS = 10
ELIMINATION_INTERVAL = 7200
VESTING_DELAY = 86400

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def vrf_mock():
    """Deploy a fresh VRF coordinator mock."""
    return mock_vrf_coordinator.deploy()


@pytest.fixture
def raffle(vrf_mock):
    """Deploy a fresh raffle with the VRF mock."""
    from contracts import raffle as rf
    from eth_utils import to_bytes

    gas_lane = to_bytes(
        hexstr="0x787d74caea10b2b357790d5b5247c2f63d1d91572a9846f780606e4d953677ae"
    )
    return rf.deploy(
        vrf_mock.address,
        0,           # subscription_id
        gas_lane,
        500000,      # callback_gas_limit
        10 ** 15,    # entrance_fee = 0.001 ETH
        30,          # interval = 30s
    )


def _make_viking(name: str, eth: int = 10 ** 18) -> str:
    addr = boa.env.generate_address(name)
    boa.env.set_balance(addr, eth)
    return addr


def _enter_n_players(raffle, n: int, prefix: str = "v") -> list:
    """Enter n unique players into the raffle, each buying 1 ticket."""
    players = []
    fee = raffle.entrance_fee()
    for i in range(n):
        v = _make_viking(f"{prefix}_{i}")
        with boa.env.prank(v):
            raffle.enter_raffle(value=fee)
        players.append(v)
    return players


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1-2 — Entry & Quadratic Pricing
# ══════════════════════════════════════════════════════════════════════════════


class TestInitialState:
    def test_state_is_open(self, raffle):
        assert raffle.raffle_state() == 1  # RaffleState.OPEN

    def test_total_players_zero(self, raffle):
        assert raffle.total_players() == 0

    def test_round_number_starts_at_one(self, raffle):
        assert raffle.round_number() == 1

    def test_entrance_fee(self, raffle):
        assert raffle.entrance_fee() == 10 ** 15

    def test_next_jackpot_zero(self, raffle):
        assert raffle.next_jackpot() == 0


class TestEnterRaffle:
    def test_first_entry(self, raffle):
        v = _make_viking("first")
        fee = raffle.entrance_fee()
        with boa.env.prank(v):
            raffle.enter_raffle(value=fee)
        assert raffle.total_players() == 1
        assert raffle.active_vikings(0) == v
        profile = raffle.player_profiles(v)
        assert profile[0] == 1      # tickets
        assert profile[1] is True   # is_alive

    def test_quadratic_pricing(self, raffle):
        v = _make_viking("quad", 10 ** 19)
        fee = raffle.entrance_fee()
        with boa.env.prank(v):
            raffle.enter_raffle(value=fee)           # 1st: 1² × fee
            raffle.enter_raffle(value=4 * fee)       # 2nd: 2² × fee
            raffle.enter_raffle(value=9 * fee)       # 3rd: 3² × fee
        profile = raffle.player_profiles(v)
        assert profile[0] == 3  # 3 tickets

    def test_insufficient_eth_reverts(self, raffle):
        v = _make_viking("poor")
        with boa.reverts("Raffle: Insufficient ETH sent"):
            with boa.env.prank(v):
                raffle.enter_raffle(value=1)

    def test_overpayment_returns_change(self, raffle):
        v = _make_viking("rich", 10 ** 19)
        fee = raffle.entrance_fee()
        overpay = fee * 10
        bal_before = boa.env.get_balance(v)
        with boa.env.prank(v):
            raffle.enter_raffle(value=overpay)
        bal_after = boa.env.get_balance(v)
        # Should have paid exactly fee, rest returned
        assert bal_before - bal_after == fee

    def test_not_open_reverts(self, raffle):
        """Cannot enter when raffle is not OPEN."""
        owner = raffle.owner()
        boa.env.time_travel(seconds=31)
        with boa.env.prank(owner):
            raffle.activate_refunds()
        v = _make_viking("late")
        with boa.reverts("Raffle: Not Open"):
            with boa.env.prank(v):
                raffle.enter_raffle(value=raffle.entrance_fee())

    def test_get_ticket_cost(self, raffle):
        v = _make_viking("cost_check")
        fee = raffle.entrance_fee()
        assert raffle.get_ticket_cost(v) == fee  # 1² × fee
        with boa.env.prank(v):
            raffle.enter_raffle(value=fee)
        assert raffle.get_ticket_cost(v) == 4 * fee  # 2² × fee


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — VRF Elimination Engine
# ══════════════════════════════════════════════════════════════════════════════


class TestElimination:
    def _setup_raffle_with_players(self, raffle, count=5):
        """Helper: enter `count` players and advance time past interval."""
        players = _enter_n_players(raffle, count)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        return players

    def test_request_elimination(self, raffle, vrf_mock):
        self._setup_raffle_with_players(raffle, 5)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        # State should be CALCULATING
        assert raffle.raffle_state() == 4  # CALCULATING

    def test_request_elimination_non_owner_reverts(self, raffle):
        self._setup_raffle_with_players(raffle, 5)
        v = _make_viking("not_owner")
        with pytest.raises(Exception):
            with boa.env.prank(v):
                raffle.request_elimination()

    def test_request_elimination_too_soon_reverts(self, raffle):
        _enter_n_players(raffle, 5)
        # Don't advance time
        owner = raffle.owner()
        with boa.reverts("Raffle: Too soon"):
            with boa.env.prank(owner):
                raffle.request_elimination()

    def test_request_elimination_3_or_fewer_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.reverts("Raffle: 3 or fewer remain"):
            with boa.env.prank(owner):
                raffle.request_elimination()

    def test_fulfill_eliminates_one(self, raffle, vrf_mock):
        self._setup_raffle_with_players(raffle, 5)
        owner = raffle.owner()

        with boa.env.prank(owner):
            raffle.request_elimination()

        # Fulfill from VRF mock
        vrf_mock.fulfillRandomWords(1, raffle.address)

        assert raffle.get_active_count() == 4
        # State should be ELIMINATING
        assert raffle.raffle_state() == 2  # ELIMINATING

    def test_fulfill_not_coordinator_reverts(self, raffle, vrf_mock):
        self._setup_raffle_with_players(raffle, 5)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()

        fake = _make_viking("faker")
        with boa.reverts("Raffle: Not VRF coordinator"):
            with boa.env.prank(fake):
                raffle.fulfillRandomWords(1, [42])

    def test_fulfill_not_calculating_reverts(self, raffle, vrf_mock):
        """fulfillRandomWords reverts if state is not CALCULATING."""
        self._setup_raffle_with_players(raffle, 5)
        # Call raffle directly as vrf coordinator (bypass mock)
        with boa.reverts("Raffle: Not calculating"):
            with boa.env.prank(vrf_mock.address):
                raffle.fulfillRandomWords(1, [42])

    def test_elimination_to_3_finishes_raffle(self, raffle, vrf_mock):
        """Eliminating down to exactly 3 survivors triggers _finish_raffle."""
        self._setup_raffle_with_players(raffle, 4)
        owner = raffle.owner()

        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)

        # Should be FINISHED now
        assert raffle.raffle_state() == 8  # FINISHED
        assert raffle.get_active_count() == 3

    def test_wrong_state_for_elimination_reverts(self, raffle, vrf_mock):
        """Cannot request elimination in FINISHED state."""
        self._setup_raffle_with_players(raffle, 4)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)
        # Now FINISHED
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        with boa.reverts("Raffle: Wrong state"):
            with boa.env.prank(owner):
                raffle.request_elimination()


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Rolling Jackpot & Tiers
# ══════════════════════════════════════════════════════════════════════════════


class TestMultiWinnerAndJackpot:
    def test_winners_assigned_after_finish(self, raffle, vrf_mock):
        _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)

        # 3 winners should be set
        for i in range(3):
            assert raffle.winners(i) != "0x0000000000000000000000000000000000000000"

    def test_prize_pool_set(self, raffle, vrf_mock):
        _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)

        assert raffle.prize_pool() > 0

    def test_tiered_payouts(self, raffle, vrf_mock):
        _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)

        total = raffle.prize_pool()
        w1 = raffle.winners(0)
        w2 = raffle.winners(1)
        w3 = raffle.winners(2)

        assert raffle.pending_claims(w1) == (total * 70) // 100
        assert raffle.pending_claims(w2) == (total * 20) // 100
        assert raffle.pending_claims(w3) == (total * 10) // 100

    def test_roll_jackpot(self, raffle):
        """Roll jackpot when raffle expires with < MIN_ENTRANTS."""
        _enter_n_players(raffle, 3)
        pot_before = raffle.get_pot_size()
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.roll_jackpot()

        assert raffle.next_jackpot() == pot_before
        assert raffle.raffle_state() == 16  # REFUNDABLE

    def test_roll_jackpot_enough_players_reverts(self, raffle):
        _enter_n_players(raffle, MIN_ENTRANTS)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.reverts("Raffle: Enough players"):
            with boa.env.prank(owner):
                raffle.roll_jackpot()

    def test_roll_jackpot_not_expired_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        owner = raffle.owner()
        with boa.reverts("Raffle: Not expired"):
            with boa.env.prank(owner):
                raffle.roll_jackpot()


# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Payout & Vesting
# ══════════════════════════════════════════════════════════════════════════════


class TestPayoutAndVesting:
    def _finish_raffle(self, raffle, vrf_mock):
        """Helper: enter 4 players, eliminate 1 → FINISHED with 3 winners."""
        players = _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)
        return players

    def test_claim_after_vesting(self, raffle, vrf_mock):
        self._finish_raffle(raffle, vrf_mock)
        winner = raffle.winners(0)
        claim_amount = raffle.pending_claims(winner)
        assert claim_amount > 0

        # Advance past vesting
        boa.env.time_travel(seconds=VESTING_DELAY + 1)
        boa.env.set_balance(winner, 0)

        with boa.env.prank(winner):
            raffle.claim_prize()

        assert raffle.pending_claims(winner) == 0
        assert boa.env.get_balance(winner) == claim_amount

    def test_claim_before_vesting_reverts(self, raffle, vrf_mock):
        self._finish_raffle(raffle, vrf_mock)
        winner = raffle.winners(0)
        with boa.reverts("Raffle: Still vesting"):
            with boa.env.prank(winner):
                raffle.claim_prize()

    def test_claim_nothing_reverts(self, raffle, vrf_mock):
        self._finish_raffle(raffle, vrf_mock)
        nobody = _make_viking("nobody")
        boa.env.time_travel(seconds=VESTING_DELAY + 1)
        with boa.reverts("Raffle: Nothing to claim"):
            with boa.env.prank(nobody):
                raffle.claim_prize()

    def test_double_claim_reverts(self, raffle, vrf_mock):
        self._finish_raffle(raffle, vrf_mock)
        winner = raffle.winners(0)
        boa.env.time_travel(seconds=VESTING_DELAY + 1)
        with boa.env.prank(winner):
            raffle.claim_prize()
        with boa.reverts("Raffle: Nothing to claim"):
            with boa.env.prank(winner):
                raffle.claim_prize()

    def test_all_three_winners_can_claim(self, raffle, vrf_mock):
        self._finish_raffle(raffle, vrf_mock)
        boa.env.time_travel(seconds=VESTING_DELAY + 1)

        for i in range(3):
            w = raffle.winners(i)
            amt = raffle.pending_claims(w)
            if amt > 0:
                boa.env.set_balance(w, 0)
                with boa.env.prank(w):
                    raffle.claim_prize()
                assert boa.env.get_balance(w) == amt


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Refund Safety-Switch
# ══════════════════════════════════════════════════════════════════════════════


class TestRefund:
    def test_activate_refunds(self, raffle):
        _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.activate_refunds()
        assert raffle.raffle_state() == 16  # REFUNDABLE

    def test_activate_refunds_enough_players_reverts(self, raffle):
        _enter_n_players(raffle, MIN_ENTRANTS)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.reverts("Raffle: Enough players joined"):
            with boa.env.prank(owner):
                raffle.activate_refunds()

    def test_activate_refunds_not_expired_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        owner = raffle.owner()
        with boa.reverts("Raffle: Not expired"):
            with boa.env.prank(owner):
                raffle.activate_refunds()

    def test_activate_refunds_non_owner_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        v = _make_viking("sneaky")
        with pytest.raises(Exception):
            with boa.env.prank(v):
                raffle.activate_refunds()

    def test_request_refund(self, raffle):
        players = _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.activate_refunds()

        p = players[0]
        contribution = raffle.player_profiles(p)[2]
        boa.env.set_balance(p, 0)

        with boa.env.prank(p):
            raffle.request_refund()

        assert boa.env.get_balance(p) == contribution
        assert raffle.player_profiles(p)[3] is True  # has_refunded

    def test_request_refund_not_refundable_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        v = _make_viking("early")
        with boa.reverts("Raffle: Not refundable"):
            with boa.env.prank(v):
                raffle.request_refund()

    def test_request_refund_no_contribution_reverts(self, raffle):
        _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.activate_refunds()

        outsider = _make_viking("outsider")
        with boa.reverts("Raffle: No contribution"):
            with boa.env.prank(outsider):
                raffle.request_refund()

    def test_double_refund_reverts(self, raffle):
        players = _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.activate_refunds()

        p = players[0]
        with boa.env.prank(p):
            raffle.request_refund()
        with boa.reverts("Raffle: Already refunded"):
            with boa.env.prank(p):
                raffle.request_refund()


# ══════════════════════════════════════════════════════════════════════════════
# Admin — Round Reset
# ══════════════════════════════════════════════════════════════════════════════


class TestRoundReset:
    def test_reset_after_finish(self, raffle, vrf_mock):
        _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)
        # FINISHED
        with boa.env.prank(owner):
            raffle.reset_round()

        assert raffle.raffle_state() == 1  # OPEN
        assert raffle.total_players() == 0
        assert raffle.round_number() == 2
        assert raffle.get_active_count() == 0

    def test_reset_after_refund(self, raffle):
        _enter_n_players(raffle, 3)
        boa.env.time_travel(seconds=31)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.activate_refunds()
        with boa.env.prank(owner):
            raffle.reset_round()
        assert raffle.raffle_state() == 1
        assert raffle.round_number() == 2

    def test_reset_wrong_state_reverts(self, raffle):
        owner = raffle.owner()
        with boa.reverts("Raffle: Round not over"):
            with boa.env.prank(owner):
                raffle.reset_round()

    def test_reset_non_owner_reverts(self, raffle, vrf_mock):
        _enter_n_players(raffle, 4)
        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)
        owner = raffle.owner()
        with boa.env.prank(owner):
            raffle.request_elimination()
        vrf_mock.fulfillRandomWords(1, raffle.address)

        v = _make_viking("hacker")
        with pytest.raises(Exception):
            with boa.env.prank(v):
                raffle.reset_round()


# ══════════════════════════════════════════════════════════════════════════════
# View Helpers
# ══════════════════════════════════════════════════════════════════════════════


class TestViewHelpers:
    def test_get_active_count(self, raffle):
        assert raffle.get_active_count() == 0
        _enter_n_players(raffle, 5)
        assert raffle.get_active_count() == 5

    def test_get_pot_size(self, raffle):
        assert raffle.get_pot_size() == 0
        _enter_n_players(raffle, 3)
        assert raffle.get_pot_size() > 0

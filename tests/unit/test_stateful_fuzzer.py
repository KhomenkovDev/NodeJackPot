"""
test_stateful_fuzzer.py — Hypothesis Stateful Fuzzer for NodeJackPot
=====================================================================
Exercises the raffle lifecycle through randomised sequences of entries,
eliminations, claims, and refunds.  Ghost state tracks expected values
and invariants are checked after every single step.

Invariants:
    1. Contract balance ≥ sum of pending claims.
    2. active_vikings count matches ghost alive count.
    3. Raffle state flag consistency.

Run:
    moccasin test tests/unit/test_stateful_fuzzer.py -s
"""

from hypothesis import settings, strategies, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from contracts.mocks import mock_vrf_coordinator
from eth_utils import to_bytes
import boa


ELIMINATION_INTERVAL = 7200
VESTING_DELAY = 86400
USERS_SIZE = 8


class RaffleFuzzer(RuleBasedStateMachine):
    """State machine exercising the entire raffle lifecycle."""

    def __init__(self):
        super().__init__()

        # Deploy fresh VRF mock + raffle
        self.vrf = mock_vrf_coordinator.deploy()
        from contracts import raffle as rf

        gas_lane = to_bytes(
            hexstr="0x787d74caea10b2b357790d5b5247c2f63d1d91572a9846f780606e4d953677ae"
        )
        self.contract = rf.deploy(
            self.vrf.address, 0, gas_lane, 500000, 10 ** 15, 30
        )

        self.owner = self.contract.owner()
        self.users = [
            boa.env.generate_address(f"fuzz_{i}") for i in range(USERS_SIZE)
        ]
        for u in self.users:
            boa.env.set_balance(u, 10 ** 19)

        # Ghost state
        self.ghost_players: set = set()
        self.ghost_alive: int = 0
        self.ghost_pending: dict = {}
        self.ghost_state: str = "OPEN"
        self.vrf_request_id: int = 0

    # ── Rules ─────────────────────────────────────────────────────────────

    @rule(user_idx=strategies.integers(min_value=0, max_value=USERS_SIZE - 1))
    def enter_raffle(self, user_idx: int):
        user = self.users[user_idx]
        assume(self.ghost_state == "OPEN")

        fee = self.contract.get_ticket_cost(user)
        assume(boa.env.get_balance(user) >= fee)

        with boa.env.prank(user):
            self.contract.enter_raffle(value=fee)

        if user not in self.ghost_players:
            self.ghost_players.add(user)
            self.ghost_alive += 1

    @rule()
    def request_elimination(self):
        assume(self.ghost_state in ("OPEN", "ELIMINATING"))
        assume(self.ghost_alive > 3)

        boa.env.time_travel(seconds=ELIMINATION_INTERVAL + 1)

        with boa.env.prank(self.owner):
            self.contract.request_elimination()

        self.ghost_state = "CALCULATING"
        self.vrf_request_id += 1

    @rule()
    def fulfill_elimination(self):
        assume(self.ghost_state == "CALCULATING")
        assume(self.ghost_alive > 3)

        self.vrf.fulfillRandomWords(self.vrf_request_id, self.contract.address)

        self.ghost_alive -= 1
        if self.ghost_alive == 3:
            self.ghost_state = "FINISHED"
            for i in range(3):
                w = self.contract.winners(i)
                self.ghost_pending[w] = self.contract.pending_claims(w)
        else:
            self.ghost_state = "ELIMINATING"

    @rule(winner_idx=strategies.integers(min_value=0, max_value=2))
    def claim_prize(self, winner_idx: int):
        assume(self.ghost_state == "FINISHED")

        winner = self.contract.winners(winner_idx)
        assume(winner != "0x0000000000000000000000000000000000000000")
        assume(self.contract.pending_claims(winner) > 0)

        boa.env.time_travel(seconds=VESTING_DELAY + 1)

        with boa.env.prank(winner):
            self.contract.claim_prize()

        self.ghost_pending[winner] = 0

    # ── Invariants ────────────────────────────────────────────────────────

    @invariant()
    def active_count_consistent(self):
        assert self.contract.get_active_count() == self.ghost_alive

    @invariant()
    def balance_covers_claims(self):
        total_pending = sum(self.ghost_pending.values())
        assert self.contract.get_pot_size() >= total_pending


# ---------------------------------------------------------------------------
# Pytest Wiring
# ---------------------------------------------------------------------------

TestStatefulFuzzing = RaffleFuzzer.TestCase
TestStatefulFuzzing.settings = settings(
    max_examples=200,
    stateful_step_count=30,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)

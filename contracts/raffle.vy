# pragma version 0.4.3
"""
@license MIT
@title NodeJackPot — Viking Elimination Raffle
@author KhomDev
@notice A provably-fair elimination raffle powered by Chainlink VRF 2.5.
        Players buy tickets with quadratic pricing, then a VRF-driven
        elimination engine removes one viking per round until 3 survivors
        split the pot (70 / 20 / 10).  Includes a rolling jackpot for
        rounds that time out, pull-payment vesting for winners, and a
        refund safety-switch when participation is too low.
@dev    Inherits Snekmate `ownable` for admin controls.  Uses
        `@nonreentrant` on all ETH-moving externals.  VRF callback is
        access-gated to the coordinator address.

Phase Summary
─────────────
 1-2  Entry & quadratic pricing (done)
 3    VRF elimination engine
 4    Rolling jackpot & multi-winner tiers (70/20/10)
 5    Payout & vesting (pull-payment pattern)
 6    Refund safety-switch
"""

from snekmate.auth import ownable as ow

initializes: ow
exports: ow.__interface__

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

## @notice Hard limit on players per round.
MAX_NUMBER_OF_PLAYERS: constant(uint256) = 1000

## @notice Minimum entrants required; below this the refund switch activates.
MIN_ENTRANTS: constant(uint256) = 10

## @notice Seconds between elimination rounds.
ELIMINATION_INTERVAL: constant(uint256) = 7200  # 2 hours

## @notice Base cost for the first ticket (quadratic pricing scales from here).
BASE_TICKET_PRICE: constant(uint256) = as_wei_value(0.001, "ether")

## @notice Seconds winners must wait after the raffle ends before claiming.
VESTING_DELAY: constant(uint256) = 86400  # 24 hours

## @notice Number of VRF random words requested per elimination call.
NUM_WORDS: constant(uint32) = 1

## @notice Tier split percentages (basis-point-like, out of 100).
TIER_1_PCT: constant(uint256) = 70
TIER_2_PCT: constant(uint256) = 20
TIER_3_PCT: constant(uint256) = 10

# ──────────────────────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────────────────────

flag RaffleState:
    OPEN
    ELIMINATING
    CALCULATING
    FINISHED
    REFUNDABLE

struct Player:
    tickets: uint256
    is_alive: bool
    contribution: uint256
    has_refunded: bool

# ──────────────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────────────

## @notice Chainlink VRF key hash.
gas_lane: public(bytes32)
## @notice Max gas for VRF callback.
callback_gas_limit: public(uint32)
## @notice Current raffle lifecycle state.
raffle_state: public(RaffleState)
## @notice Address of the VRF coordinator (mock or mainnet).
vrf_coordinator: public(address)
## @notice Chainlink VRF subscription ID.
subscription_id: public(uint256)
## @notice Current entrance fee (= BASE_TICKET_PRICE).
entrance_fee: public(uint256)
## @notice Duration before the raffle can start eliminations.
raffle_duration: public(uint256)
## @notice Timestamp of last state-changing action (deploy / elimination).
last_timestamp: public(uint256)
## @notice Per-address player data.
player_profiles: public(HashMap[address, Player])
## @notice Ordered list of currently alive players.
active_vikings: public(DynArray[address, MAX_NUMBER_OF_PLAYERS])
## @notice Total unique players who entered this round.
total_players: public(uint256)

## @notice Jackpot rolled over from a previous round that timed out.
next_jackpot: public(uint256)

## @notice Timestamp of last VRF-driven elimination.
last_elimination: public(uint256)

## @notice Pending claim amounts for each winner (pull-payment vault).
pending_claims: public(HashMap[address, uint256])
## @notice Earliest timestamp a winner may withdraw their claim.
unlock_time: public(HashMap[address, uint256])

## @notice Deadline (timestamp) after which a low-turnout round becomes refundable.
raffle_deadline: public(uint256)

## @notice The three winners of the round (index 0 = 1st place).
winners: public(address[3])

## @notice Total prize pool available for distribution.
prize_pool: public(uint256)

## @notice Round counter for off-chain indexing.
round_number: public(uint256)

# ──────────────────────────────────────────────────────────────────────────────
# Events
# ──────────────────────────────────────────────────────────────────────────────

event RaffleEntered:
    player: indexed(address)
    tickets: uint256
    paid: uint256

event EliminationRequested:
    request_id: uint256

event VikingEliminated:
    loser: indexed(address)
    remaining: uint256

event RaffleFinished:
    first: indexed(address)
    second: indexed(address)
    third: indexed(address)
    prize_pool: uint256

event WinnerPaid:
    winner: indexed(address)
    amount: uint256

event RefundIssued:
    player: indexed(address)
    amount: uint256

event JackpotRolled:
    amount: uint256
    new_round: uint256

event RoundReset:
    new_round: uint256

# ──────────────────────────────────────────────────────────────────────────────
# Constructor
# ──────────────────────────────────────────────────────────────────────────────

@deploy
def __init__(
    _vrf_coordinator: address,
    _subscription_id: uint256,
    _gas_lane: bytes32,
    _callback_gas_limit: uint32,
    _entrance_fee: uint256,
    _interval: uint256,
):
    """
    @notice Deploy the Viking Raffle.
    @param _vrf_coordinator  Chainlink VRF Coordinator (or mock) address.
    @param _subscription_id  VRF subscription ID.
    @param _gas_lane         VRF key hash.
    @param _callback_gas_limit  Max callback gas.
    @param _entrance_fee     Base ticket price in wei.
    @param _interval         Raffle duration in seconds.
    """
    ow.__init__()
    self.raffle_state = RaffleState.OPEN
    self.last_timestamp = block.timestamp
    self.last_elimination = block.timestamp

    self.vrf_coordinator = _vrf_coordinator
    self.subscription_id = _subscription_id
    self.gas_lane = _gas_lane
    self.callback_gas_limit = _callback_gas_limit
    self.entrance_fee = _entrance_fee
    self.raffle_duration = _interval
    self.raffle_deadline = block.timestamp + _interval

    self.round_number = 1

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1-2 — Entry & Quadratic Pricing
# ══════════════════════════════════════════════════════════════════════════════

@external
@payable
@nonreentrant
def enter_raffle():
    """
    @notice Buy the next ticket at quadratic cost.
    @dev    Cost = (current_tickets + 1)² × entrance_fee.
            Overpayment is refunded as change.
    """
    assert self.raffle_state == RaffleState.OPEN, "Raffle: Not Open"

    current_tickets: uint256 = self.player_profiles[msg.sender].tickets
    new_total_tickets: uint256 = current_tickets + 1
    required_eth: uint256 = (new_total_tickets ** 2) * self.entrance_fee
    assert msg.value >= required_eth, "Raffle: Insufficient ETH sent"

    # First-time player bookkeeping
    if current_tickets == 0:
        self.active_vikings.append(msg.sender)
        self.total_players += 1

    self.player_profiles[msg.sender].tickets = new_total_tickets
    self.player_profiles[msg.sender].contribution += msg.value
    self.player_profiles[msg.sender].is_alive = True

    log RaffleEntered(player=msg.sender, tickets=new_total_tickets, paid=msg.value)

    # Return overpayment
    change: uint256 = msg.value - required_eth
    if change > 0:
        send(msg.sender, change)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — The Elimination Engine (VRF)
# ══════════════════════════════════════════════════════════════════════════════

@external
def request_elimination():
    """
    @notice Owner triggers a VRF request to eliminate one viking.
    @dev    Requires the raffle to be OPEN or ELIMINATING, enough time
            since the last elimination, and more than 3 active vikings.
    """
    ow._check_owner()
    assert (
        self.raffle_state == RaffleState.OPEN or
        self.raffle_state == RaffleState.ELIMINATING
    ), "Raffle: Wrong state"
    assert block.timestamp >= self.last_elimination + ELIMINATION_INTERVAL, "Raffle: Too soon"
    assert len(self.active_vikings) > 3, "Raffle: 3 or fewer remain"

    self.raffle_state = RaffleState.CALCULATING

    # Call the VRF coordinator
    response: Bytes[32] = raw_call(
        self.vrf_coordinator,
        concat(
            method_id("requestRandomWords(bytes32,uint256,uint16,uint32,uint32,bytes)"),
            abi_encode(
                self.gas_lane,
                self.subscription_id,
                convert(3, uint16),               # confirmations
                self.callback_gas_limit,
                NUM_WORDS,
                b"",
            ),
        ),
        max_outsize=32,
    )
    request_id: uint256 = convert(extract32(response, 0), uint256)

    log EliminationRequested(request_id=request_id)

@external
def fulfillRandomWords(request_id: uint256, random_words: DynArray[uint256, 10]):
    """
    @notice VRF callback — eliminate one viking using the random word.
    @dev    Access-gated to the VRF coordinator address.
    """
    assert msg.sender == self.vrf_coordinator, "Raffle: Not VRF coordinator"
    assert self.raffle_state == RaffleState.CALCULATING, "Raffle: Not calculating"

    active_count: uint256 = len(self.active_vikings)
    assert active_count > 3, "Raffle: Cannot eliminate below 3"

    # Pick a loser
    loser_index: uint256 = random_words[0] % active_count
    loser: address = self.active_vikings[loser_index]

    # Mark as dead
    self.player_profiles[loser].is_alive = False

    # Swap-and-pop removal from active list
    last_index: uint256 = active_count - 1
    if loser_index != last_index:
        self.active_vikings[loser_index] = self.active_vikings[last_index]
    self.active_vikings.pop()

    self.last_elimination = block.timestamp

    remaining: uint256 = len(self.active_vikings)

    log VikingEliminated(loser=loser, remaining=remaining)

    # Check if we have exactly 3 survivors → finish the round
    if remaining == 3:
        self._finish_raffle()
    else:
        self.raffle_state = RaffleState.ELIMINATING

# ══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Rolling Jackpot & Multi-Winner Tiers
# ══════════════════════════════════════════════════════════════════════════════

@internal
def _finish_raffle():
    """
    @notice Finalise the round: assign 3 winners, calculate tiered payouts,
            and move state to FINISHED.
    """
    self.raffle_state = RaffleState.FINISHED

    self.winners[0] = self.active_vikings[0]  # 1st place — 70 %
    self.winners[1] = self.active_vikings[1]  # 2nd place — 20 %
    self.winners[2] = self.active_vikings[2]  # 3rd place — 10 %

    total: uint256 = self.balance + self.next_jackpot
    self.prize_pool = total

    payout_1: uint256 = (total * TIER_1_PCT) // 100
    payout_2: uint256 = (total * TIER_2_PCT) // 100
    payout_3: uint256 = (total * TIER_3_PCT) // 100

    now: uint256 = block.timestamp

    self.pending_claims[self.winners[0]] = payout_1
    self.unlock_time[self.winners[0]] = now + VESTING_DELAY

    self.pending_claims[self.winners[1]] = payout_2
    self.unlock_time[self.winners[1]] = now + VESTING_DELAY

    self.pending_claims[self.winners[2]] = payout_3
    self.unlock_time[self.winners[2]] = now + VESTING_DELAY

    self.next_jackpot = 0  # consumed

    log RaffleFinished(
        first=self.winners[0],
        second=self.winners[1],
        third=self.winners[2],
        prize_pool=total,
    )

@external
def roll_jackpot():
    """
    @notice Owner rolls the current balance into the next round if the
            raffle times out without reaching elimination phase.
    @dev    Can only be called when OPEN and past the deadline with
            fewer than MIN_ENTRANTS.
    """
    ow._check_owner()
    assert self.raffle_state == RaffleState.OPEN, "Raffle: Not open"
    assert block.timestamp >= self.raffle_deadline, "Raffle: Not expired"
    assert self.total_players < MIN_ENTRANTS, "Raffle: Enough players"

    rolled: uint256 = self.balance
    self.next_jackpot += rolled
    self.raffle_state = RaffleState.REFUNDABLE

    log JackpotRolled(amount=rolled, new_round=self.round_number + 1)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Payout & Vesting (Pull-Payment)
# ══════════════════════════════════════════════════════════════════════════════

@external
@nonreentrant
def claim_prize():
    """
    @notice Winners call this to withdraw their share after the vesting
            delay has elapsed.
    @dev    Uses the pull-payment pattern with reentrancy protection.
    """
    amount: uint256 = self.pending_claims[msg.sender]
    assert amount > 0, "Raffle: Nothing to claim"
    assert block.timestamp >= self.unlock_time[msg.sender], "Raffle: Still vesting"

    self.pending_claims[msg.sender] = 0
    self.unlock_time[msg.sender] = 0

    send(msg.sender, amount)

    log WinnerPaid(winner=msg.sender, amount=amount)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Refund Safety-Switch
# ══════════════════════════════════════════════════════════════════════════════

@external
def activate_refunds():
    """
    @notice Owner activates refund mode if the raffle expired with fewer
            than MIN_ENTRANTS and the state is still OPEN.
    """
    ow._check_owner()
    assert self.raffle_state == RaffleState.OPEN, "Raffle: Not open"
    assert block.timestamp >= self.raffle_deadline, "Raffle: Not expired"
    assert self.total_players < MIN_ENTRANTS, "Raffle: Enough players joined"

    self.raffle_state = RaffleState.REFUNDABLE

@external
@nonreentrant
def request_refund():
    """
    @notice Players reclaim their original ETH contribution when the raffle
            has entered REFUNDABLE state.
    """
    assert self.raffle_state == RaffleState.REFUNDABLE, "Raffle: Not refundable"

    player: Player = self.player_profiles[msg.sender]
    assert player.contribution > 0, "Raffle: No contribution"
    assert not player.has_refunded, "Raffle: Already refunded"

    self.player_profiles[msg.sender].has_refunded = True
    refund_amount: uint256 = player.contribution

    send(msg.sender, refund_amount)

    log RefundIssued(player=msg.sender, amount=refund_amount)

# ══════════════════════════════════════════════════════════════════════════════
# Admin Helpers
# ══════════════════════════════════════════════════════════════════════════════

@external
def reset_round():
    """
    @notice Owner resets the raffle for a new round after the current one
            has finished or been refunded.
    """
    ow._check_owner()
    assert (
        self.raffle_state == RaffleState.FINISHED or
        self.raffle_state == RaffleState.REFUNDABLE
    ), "Raffle: Round not over"

    # Clear active list
    for _v: address in self.active_vikings:
        self.player_profiles[_v] = empty(Player)

    self.active_vikings = []
    self.total_players = 0
    self.round_number += 1
    self.raffle_state = RaffleState.OPEN
    self.last_timestamp = block.timestamp
    self.last_elimination = block.timestamp
    self.raffle_deadline = block.timestamp + self.raffle_duration
    self.prize_pool = 0

    for i: uint256 in range(3):
        self.winners[i] = empty(address)

    log RoundReset(new_round=self.round_number)

# ══════════════════════════════════════════════════════════════════════════════
# View Helpers
# ══════════════════════════════════════════════════════════════════════════════

@external
@view
def get_active_count() -> uint256:
    """@notice Returns the number of currently alive vikings."""
    return len(self.active_vikings)

@external
@view
def get_pot_size() -> uint256:
    """@notice Returns the current contract balance (prize pool)."""
    return self.balance

@external
@view
def get_ticket_cost(player: address) -> uint256:
    """
    @notice Returns the cost for the player's NEXT ticket.
    @param player  Address to quote.
    @return The wei cost of the next ticket.
    """
    current: uint256 = self.player_profiles[player].tickets
    next_ticket: uint256 = current + 1
    return (next_ticket ** 2) * self.entrance_fee

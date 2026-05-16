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
"""

from snekmate.auth import ownable as ow

initializes: ow
exports: ow.__interface__

# ──────────────────────────────────────────────────────────────────────────────
# Chainlink VRF V2.5 — request struct + interface
# ──────────────────────────────────────────────────────────────────────────────
#
# The coordinator's `requestRandomWords` takes ONE tuple parameter — the
# `RandomWordsRequest` struct — not flat positional args. Calling the flat
# variant via raw_call(method_id("requestRandomWords(bytes32,uint256,...)"))
# produces a selector that does not exist on the live coordinator and fails
# on mainnet. We use a proper Vyper interface so the encoding is correct.

struct RandomWordsRequest:
    keyHash: bytes32
    subId: uint256
    requestConfirmations: uint16
    callbackGasLimit: uint32
    numWords: uint32
    extraArgs: Bytes[256]

interface IVRFCoordinatorV2Plus:
    def requestRandomWords(req: RandomWordsRequest) -> uint256: nonpayable

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

## @notice Hard limit on players per round.
MAX_NUMBER_OF_PLAYERS: constant(uint256) = 1000

## @notice Minimum entrants required; below this the refund switch activates.
MIN_ENTRANTS: constant(uint256) = 10

## @notice Seconds between elimination rounds.
ELIMINATION_INTERVAL: constant(uint256) = 7200  # 2 hours

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
    round_id: uint256

# ──────────────────────────────────────────────────────────────────────────────
# Immutables
# ──────────────────────────────────────────────────────────────────────────────

VRF_COORDINATOR: immutable(address)
SUBSCRIPTION_ID: immutable(uint256)
GAS_LANE: immutable(bytes32)
CALLBACK_GAS_LIMIT: immutable(uint32)
ENTRANCE_FEE: immutable(uint256)
RAFFLE_DURATION: immutable(uint256)

# ──────────────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────────────

## @notice Current raffle lifecycle state.
raffle_state: public(RaffleState)

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

## @notice Round counter for off-chain indexing and state validation.
round_number: public(uint256)

# ──────────────────────────────────────────────────────────────────────────────
# Events
# ──────────────────────────────────────────────────────────────────────────────

event RaffleEntered:
    player: indexed(address)
    round_id: indexed(uint256)
    tickets: uint256
    paid: uint256

event EliminationRequested:
    round_id: indexed(uint256)
    request_id: uint256

event VikingEliminated:
    round_id: indexed(uint256)
    loser: indexed(address)
    remaining: uint256

event RaffleFinished:
    round_id: indexed(uint256)
    first: indexed(address)
    second: indexed(address)
    third: address
    prize_pool: uint256

event WinnerPaid:
    winner: indexed(address)
    amount: uint256

event RefundIssued:
    round_id: indexed(uint256)
    player: indexed(address)
    amount: uint256

event JackpotRolled:
    from_round: indexed(uint256)
    amount: uint256
    new_round: uint256

event RoundReset:
    old_round: indexed(uint256)
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
    @notice Initialize the Viking Raffle with core parameters.
    @param _vrf_coordinator The Chainlink VRF Coordinator address.
    @param _subscription_id The VRF subscription ID for funding requests.
    @param _gas_lane The key hash identifying the desired gas lane.
    @param _callback_gas_limit Maximum gas for the VRF callback function.
    @param _entrance_fee The base cost for the first ticket in a round.
    @param _interval The duration (in seconds) of the entry phase.
    """
    ow.__init__()
    self.raffle_state = RaffleState.OPEN
    self.last_elimination = block.timestamp
    self.round_number = 1
    self.raffle_deadline = block.timestamp + _interval

    VRF_COORDINATOR = _vrf_coordinator
    SUBSCRIPTION_ID = _subscription_id
    GAS_LANE = _gas_lane
    CALLBACK_GAS_LIMIT = _callback_gas_limit
    ENTRANCE_FEE = _entrance_fee
    RAFFLE_DURATION = _interval

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1-2 — Entry & Quadratic Pricing
# ══════════════════════════════════════════════════════════════════════════════

@external
@payable
@nonreentrant
def enter_raffle():
    """
    @notice Purchase the next ticket for the current round using quadratic pricing.
    @dev    Formula: Cost = (current_tickets + 1)² × ENTRANCE_FEE.
            Excess ETH is returned as change to the sender.
            First-time entrants are added to the `active_vikings` registry.
    """
    assert self.raffle_state == RaffleState.OPEN, "Raffle: Not Open"
    
    # Ensure profile is current for the round
    player: Player = self.player_profiles[msg.sender]
    current_tickets: uint256 = 0
    if player.round_id == self.round_number:
        current_tickets = player.tickets
    
    new_total_tickets: uint256 = current_tickets + 1
    required_eth: uint256 = (new_total_tickets ** 2) * ENTRANCE_FEE
    assert msg.value >= required_eth, "Raffle: Insufficient ETH sent"

    # Registry management for new warriors
    if current_tickets == 0:
        self.active_vikings.append(msg.sender)
        self.total_players += 1

    # Update state
    self.player_profiles[msg.sender] = Player(
        tickets=new_total_tickets,
        is_alive=True,
        contribution=player.contribution + msg.value if player.round_id == self.round_number else msg.value,
        has_refunded=False,
        round_id=self.round_number
    )

    log RaffleEntered(player=msg.sender, round_id=self.round_number, tickets=new_total_tickets, paid=msg.value)

    # Process change
    change: uint256 = msg.value - required_eth
    if change > 0:
        send(msg.sender, change)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — The Elimination Engine (VRF)
# ══════════════════════════════════════════════════════════════════════════════

@external
def request_elimination():
    """
    @notice Initiate a randomness request to eliminate one Viking from the current round.
    @dev    Only the owner can trigger eliminations.
            Requires proper timing (ELIMINATION_INTERVAL) and enough survivors.
    """
    ow._check_owner()
    assert (
        self.raffle_state == RaffleState.OPEN or
        self.raffle_state == RaffleState.ELIMINATING
    ), "Raffle: Wrong state"
    assert block.timestamp >= self.last_elimination + ELIMINATION_INTERVAL, "Raffle: Too soon"
    assert len(self.active_vikings) > 3, "Raffle: 3 or fewer remain"

    self.raffle_state = RaffleState.CALCULATING

    # Trigger VRF 2.5 Request — single struct parameter, not flat positionals.
    request: RandomWordsRequest = RandomWordsRequest(
        keyHash=GAS_LANE,
        subId=SUBSCRIPTION_ID,
        requestConfirmations=3,
        callbackGasLimit=CALLBACK_GAS_LIMIT,
        numWords=NUM_WORDS,
        extraArgs=b"",
    )
    request_id: uint256 = extcall IVRFCoordinatorV2Plus(VRF_COORDINATOR).requestRandomWords(request)

    log EliminationRequested(round_id=self.round_number, request_id=request_id)

@external
def fulfillRandomWords(request_id: uint256, random_words: DynArray[uint256, 10]):
    """
    @notice Callback from Chainlink VRF Coordinator to process elimination.
    @param request_id Unique identifier for the randomness request.
    @param random_words Array of random values returned by the VRF.
    @dev    Uses swap-and-pop for efficient array deletion.
            Automatically triggers `_finish_raffle` when exactly 3 survivors remain.
    """
    assert msg.sender == VRF_COORDINATOR, "Raffle: Not VRF coordinator"
    assert self.raffle_state == RaffleState.CALCULATING, "Raffle: Not calculating"

    active_count: uint256 = len(self.active_vikings)
    assert active_count > 3, "Raffle: Cannot eliminate below 3"

    # Determine the fallen warrior
    loser_index: uint256 = random_words[0] % active_count
    loser: address = self.active_vikings[loser_index]

    # Mark as eliminated
    self.player_profiles[loser].is_alive = False

    # Efficient Swap-and-Pop
    last_index: uint256 = active_count - 1
    if loser_index != last_index:
        self.active_vikings[loser_index] = self.active_vikings[last_index]
    self.active_vikings.pop()

    self.last_elimination = block.timestamp
    remaining: uint256 = len(self.active_vikings)

    log VikingEliminated(round_id=self.round_number, loser=loser, remaining=remaining)

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
    @notice Assign prizes to the final three survivors based on tiered splits.
    @dev    Winners are moved to the pull-payment vault with a vesting lock.
            Clears the round's jackpot state.
    """
    self.raffle_state = RaffleState.FINISHED

    self.winners[0] = self.active_vikings[0]
    self.winners[1] = self.active_vikings[1]
    self.winners[2] = self.active_vikings[2]

    total: uint256 = self.balance + self.next_jackpot
    self.prize_pool = total

    # Payout calculations (70/20/10)
    payout_1: uint256 = (total * TIER_1_PCT) // 100
    payout_2: uint256 = (total * TIER_2_PCT) // 100
    payout_3: uint256 = (total * TIER_3_PCT) // 100

    unlock_ts: uint256 = block.timestamp + VESTING_DELAY

    for i: uint256 in range(3):
        winner: address = self.winners[i]
        payout: uint256 = 0
        if i == 0: payout = payout_1
        elif i == 1: payout = payout_2
        else: payout = payout_3
        
        self.pending_claims[winner] += payout
        self.unlock_time[winner] = unlock_ts

    self.next_jackpot = 0

    log RaffleFinished(
        round_id=self.round_number,
        first=self.winners[0],
        second=self.winners[1],
        third=self.winners[2],
        prize_pool=total
    )

@external
def roll_jackpot():
    """
    @notice Rollover current round funds into the next round's jackpot.
    @dev    Activated if minimum participation isn't met by the deadline.
    """
    ow._check_owner()
    assert self.raffle_state == RaffleState.OPEN, "Raffle: Not open"
    assert block.timestamp >= self.raffle_deadline, "Raffle: Not expired"
    assert self.total_players < MIN_ENTRANTS, "Raffle: Enough players"

    rolled: uint256 = self.balance
    self.next_jackpot += rolled
    self.raffle_state = RaffleState.REFUNDABLE

    log JackpotRolled(from_round=self.round_number, amount=rolled, new_round=self.round_number + 1)

# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Payout & Vesting (Pull-Payment)
# ══════════════════════════════════════════════════════════════════════════════

@external
@nonreentrant
def claim_prize():
    """
    @notice Withdraw matured winnings from the protocol vault.
    @dev    Implements pull-payment pattern to mitigate reentrancy and gas griefing.
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
    @notice Enable the refund safety-switch if the raffle fails to meet requirements.
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
    @notice Reclaim ETH contribution if the round is cancelled.
    """
    assert self.raffle_state == RaffleState.REFUNDABLE, "Raffle: Not refundable"

    player: Player = self.player_profiles[msg.sender]
    assert player.round_id == self.round_number, "Raffle: No contribution"
    assert player.contribution > 0, "Raffle: No contribution"
    assert not player.has_refunded, "Raffle: Already refunded"

    self.player_profiles[msg.sender].has_refunded = True
    refund_amount: uint256 = player.contribution

    send(msg.sender, refund_amount)

    log RefundIssued(round_id=self.round_number, player=msg.sender, amount=refund_amount)

# ══════════════════════════════════════════════════════════════════════════════
# Admin Helpers
# ══════════════════════════════════════════════════════════════════════════════

@external
def reset_round():
    """
    @notice Transition the contract to a fresh round.
    @dev    Increments `round_number` to invalidate old player profiles instantly.
    """
    ow._check_owner()
    assert (
        self.raffle_state == RaffleState.FINISHED or
        self.raffle_state == RaffleState.REFUNDABLE
    ), "Raffle: Round not over"

    old_round: uint256 = self.round_number
    self.active_vikings = []
    self.total_players = 0
    self.round_number += 1
    self.raffle_state = RaffleState.OPEN
    self.last_elimination = block.timestamp
    self.raffle_deadline = block.timestamp + RAFFLE_DURATION
    self.prize_pool = 0

    for i: uint256 in range(3):
        self.winners[i] = empty(address)

    log RoundReset(old_round=old_round, new_round=self.round_number)

# ══════════════════════════════════════════════════════════════════════════════
# View Helpers
# ══════════════════════════════════════════════════════════════════════════════

@external
@view
def entrance_fee() -> uint256:
    """@notice Compatibility getter for the base ticket price."""
    return ENTRANCE_FEE

@external
@view
def raffle_duration() -> uint256:
    """@notice Compatibility getter for the round duration."""
    return RAFFLE_DURATION

@external
@view
def vrf_coordinator() -> address:
    """@notice Compatibility getter for the VRF coordinator."""
    return VRF_COORDINATOR

@external
@view
def subscription_id() -> uint256:
    """@notice Compatibility getter for the VRF subscription ID."""
    return SUBSCRIPTION_ID

@external
@view
def gas_lane() -> bytes32:
    """@notice Compatibility getter for the VRF gas lane."""
    return GAS_LANE

@external
@view
def callback_gas_limit() -> uint32:
    """@notice Compatibility getter for the VRF callback gas limit."""
    return CALLBACK_GAS_LIMIT

@external
@view
def get_active_count() -> uint256:
    """@notice Returns the count of Vikings still in the current battle."""
    return len(self.active_vikings)

@external
@view
def get_pot_size() -> uint256:
    """@notice Returns the total ETH currently held in the prize pool."""
    return self.balance

@external
@view
def get_ticket_cost(player: address) -> uint256:
    """
    @notice Calculate the cost of the next ticket for a specific player.
    @param player The address of the Viking.
    """
    current_tickets: uint256 = 0
    if self.player_profiles[player].round_id == self.round_number:
        current_tickets = self.player_profiles[player].tickets
    
    next_ticket: uint256 = current_tickets + 1
    return (next_ticket ** 2) * ENTRANCE_FEE

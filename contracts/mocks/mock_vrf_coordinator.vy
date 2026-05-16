# pragma version 0.4.3

"""
@title MockVRFCoordinatorV2Plus
@notice Minimal Chainlink VRF V2.5 coordinator mock for tests.
@dev    The V2.5 `requestRandomWords` takes a SINGLE struct parameter
        (`RandomWordsRequest`), not flat positional args. This mock was
        previously written with the flat signature — tests passed against
        the mock but the production raffle reverted on mainnet because the
        flat selector doesn't exist on the live coordinator. Both contract
        and mock are now aligned on the correct struct ABI.
"""

# Mirror of the request struct that the live Chainlink VRF V2.5 coordinator
# expects. Field order matters — it defines the ABI tuple layout.
struct RandomWordsRequest:
    keyHash: bytes32
    subId: uint256
    requestConfirmations: uint16
    callbackGasLimit: uint32
    numWords: uint32
    extraArgs: Bytes[256]

# Event emitted when the Raffle requests randomness (kept compatible with the
# previous event shape so existing tests can still match on log args).
event RandomWordsRequested:
    keyHash: indexed(bytes32)
    requestId: uint256
    preSeed: uint256
    subId: indexed(uint256)
    minimumRequestConfirmations: uint16
    callbackGasLimit: uint32
    numWords: uint32
    extraArgs: Bytes[256]
    sender: indexed(address)


struct Request:
    sender: address
    callbackGasLimit: uint32
    numWords: uint32


next_request_id: uint256
requests: HashMap[uint256, Request]


@deploy
def __init__():
    self.next_request_id = 1


@external
def requestRandomWords(req: RandomWordsRequest) -> uint256:
    """
    @notice V2.5-compatible request entrypoint. Accepts a single struct param.
    """
    request_id: uint256 = self.next_request_id

    self.requests[request_id] = Request(
        sender=msg.sender,
        callbackGasLimit=req.callbackGasLimit,
        numWords=req.numWords,
    )

    log RandomWordsRequested(
        keyHash=req.keyHash,
        requestId=request_id,
        preSeed=0,
        subId=req.subId,
        minimumRequestConfirmations=req.requestConfirmations,
        callbackGasLimit=req.callbackGasLimit,
        numWords=req.numWords,
        extraArgs=req.extraArgs,
        sender=msg.sender,
    )

    self.next_request_id += 1
    return request_id


@external
def fulfillRandomWords(request_id: uint256, consumer: address):
    """
    @notice Test helper — synthesises random words for `request_id` and
            invokes the consumer's `fulfillRandomWords` callback.
    """
    request: Request = self.requests[request_id]
    assert request.sender != empty(address), "Request does not exist"

    random_words: DynArray[uint256, 10] = []
    for i: uint256 in range(convert(request.numWords, uint256), bound=10):
        random_words.append(convert(keccak256(convert(request_id + i, bytes32)), uint256))

    raw_call(
        consumer,
        concat(
            method_id("fulfillRandomWords(uint256,uint256[])"),
            abi_encode(request_id, random_words),
        ),
    )

    self.requests[request_id] = empty(Request)

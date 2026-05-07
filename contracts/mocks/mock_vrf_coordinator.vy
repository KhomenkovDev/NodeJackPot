# pragma version 0.4.3

# Event emitted when the Raffle requests randomness
event RandomWordsRequested:
    keyHash: indexed(bytes32)
    requestId: uint256
    preSeed: uint256
    subId: indexed(uint256)
    minimumRequestConfirmations: uint16
    callbackGasLimit: uint32
    numWords: uint32
    extraArgs: Bytes[1000]  # FIXED: Added length
    sender: indexed(address)

struct Request:
    sender: address
    callbackGasLimit: uint32
    numWords: uint32

# Storage
next_request_id: uint256
requests: HashMap[uint256, Request]

@deploy  # FIXED: Changed from @external
def __init__():
    self.next_request_id = 1

@external
def requestRandomWords(
    keyHash: bytes32,
    subId: uint256,
    minimumRequestConfirmations: uint16,
    callbackGasLimit: uint32,
    numWords: uint32,
    extraArgs: Bytes[1000] = b""  # FIXED: Added length
) -> uint256:
    request_id: uint256 = self.next_request_id
    
    self.requests[request_id] = Request(
        sender=msg.sender,
        callbackGasLimit=callbackGasLimit,
        numWords=numWords
    )
    
    log RandomWordsRequested(
            keyHash=keyHash,
            requestId=request_id,
            preSeed=0,
            subId=subId,
            minimumRequestConfirmations=minimumRequestConfirmations,
            callbackGasLimit=callbackGasLimit,
            numWords=numWords,
            extraArgs=extraArgs,
            sender=msg.sender
        )    
    self.next_request_id += 1
    return request_id

@external
def fulfillRandomWords(request_id: uint256, consumer: address):
    request: Request = self.requests[request_id]
    assert request.sender != empty(address), "Request does not exist"
    
    random_words: DynArray[uint256, 10] = []
    for i: uint256 in range(convert(request.numWords, uint256), bound=10):
        random_words.append(convert(keccak256(convert(request_id + i, bytes32)), uint256))

    # raw_call stays the same
    raw_call(
        consumer,
        concat(
            method_id("fulfillRandomWords(uint256,uint256[])"),
            abi_encode(request_id, random_words)
        )
    )
    
    self.requests[request_id] = empty(Request)
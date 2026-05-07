"""
deploy_raffle.py — NodeJackPot Deployment Script
==================================================
Deploys the Viking Elimination Raffle via the Moccasin framework.

Usage:
    mox run script/deploy_raffle.py           # local pyevm (mock VRF)
    mox run script/deploy_raffle.py --network anvil
"""

from contracts import raffle as rf
from contracts.mocks import mock_vrf_coordinator
from eth_utils import to_bytes
from moccasin.config import get_active_network


def deploy_raffle():
    """Deploy the raffle with a mock VRF coordinator for local networks."""
    active_network = get_active_network()

    print(f"⚔️  Working on network: {active_network.name}")

    # Deploy VRF mock for local environments
    if active_network.name in ("pyevm", "anvil"):
        print("   Deploying VRF Mock...")
        vrf_mock = mock_vrf_coordinator.deploy()
        vrf_address = vrf_mock.address
    else:
        vrf_address = active_network.manifest_named("mock_vrf_coordinator")

    params = active_network.extra_data
    print(f"   VRF Coordinator : {vrf_address}")

    raffle_contract = rf.deploy(
        vrf_address,
        params["subscription_id"],
        to_bytes(hexstr=params["gas_lane"]),
        params["callback_gas_limit"],
        int(params["entrance_fee"]),
        params["interval"],
    )

    print(f"✅ RAFFLE DEPLOYED AT : {raffle_contract.address}")
    print(f"   Entrance Fee      : {raffle_contract.entrance_fee() / 10**18} ETH")
    print(f"   Raffle Duration   : {raffle_contract.raffle_duration()}s")
    print(f"   Owner             : {raffle_contract.owner()}")
    return raffle_contract


def moccasin_main():
    return deploy_raffle()
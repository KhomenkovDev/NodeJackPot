'use client';

import { useReadContracts, useAccount } from 'wagmi';
import { RAFFLE_ABI, NODE_JACKPOT_ADDRESS } from '@/lib/contracts';

export function useJackpotData() {
  const { address } = useAccount();

  const { data, isLoading, refetch } = useReadContracts({
    contracts: [
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'get_pot_size',
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'total_players',
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'raffle_state',
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'get_active_count',
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'entrance_fee',
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'player_profiles',
        args: address ? [address] : undefined,
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'pending_claims',
        args: address ? [address] : undefined,
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'unlock_time',
        args: address ? [address] : undefined,
      },
      {
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'round_number',
      }
    ],
    query: {
      refetchInterval: 5000, // Real-time contract polling
    }
  });

  return {
    potSize: data?.[0]?.result as bigint | undefined,
    totalPlayers: data?.[1]?.result as bigint | undefined,
    raffleState: data?.[2]?.result as bigint | undefined, // 0: OPEN, 1: ELIMINATING, 2: CALCULATING, 3: FINISHED, 4: REFUNDABLE
    activeVikings: data?.[3]?.result as bigint | undefined,
    entranceFee: data?.[4]?.result as bigint | undefined,
    // The contract's `Player` struct has FIVE fields (in this order):
    //   tickets, is_alive, contribution, has_refunded, round_id
    // The previous declaration was missing `round_id`. Reading index 4 on a
    // 4-element tuple would silently yield `undefined` — which was the
    // "minor frontend data type mismatch" flagged by the audit.
    playerProfile: data?.[5]?.result as
        | readonly [tickets: bigint, isAlive: boolean, contribution: bigint, hasRefunded: boolean, roundId: bigint]
        | undefined,
    pendingClaim: data?.[6]?.result as bigint | undefined,
    unlockTime: data?.[7]?.result as bigint | undefined,
    roundNumber: data?.[8]?.result as bigint | undefined,
    isLoading,
    refetch,
  };
}

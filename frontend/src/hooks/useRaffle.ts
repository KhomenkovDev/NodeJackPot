'use client';

import { useWriteContract, useWaitForTransactionReceipt, useAccount } from 'wagmi';
import { RAFFLE_ABI, NODE_JACKPOT_ADDRESS } from '@/lib/contracts';
import { toast } from 'sonner';
import { parseEther } from 'viem';

export function useRaffle() {
  const { address } = useAccount();
  const { writeContractAsync, data: hash, isPending } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const handleError = (error: any) => {
    console.error('Raffle Action Error:', error);
    const message = error.shortMessage || error.message || 'Transaction failed';
    toast.error(message);
  };

  const enterRaffle = async (value: bigint) => {
    try {
      const promise = writeContractAsync({
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'enter_raffle',
        value: value,
      });

      toast.promise(promise, {
        loading: 'Entering the mead hall...',
        success: 'Welcome to the raffle, Viking!',
        error: (err) => err.shortMessage || 'Failed to enter raffle',
      });

      return await promise;
    } catch (error) {
      handleError(error);
    }
  };

  const requestElimination = async () => {
    try {
      const promise = writeContractAsync({
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'request_elimination',
      });

      toast.promise(promise, {
        loading: 'Consulting the Norns (VRF)...',
        success: 'Elimination sequence initiated!',
        error: (err) => err.shortMessage || 'Failed to request elimination',
      });

      return await promise;
    } catch (error) {
      handleError(error);
    }
  };

  const claimPrize = async () => {
    try {
      const promise = writeContractAsync({
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'claim_prize',
      });

      toast.promise(promise, {
        loading: 'Claiming your hard-earned loot...',
        success: 'Prizes successfully claimed!',
        error: (err) => err.shortMessage || 'Failed to claim prize',
      });

      return await promise;
    } catch (error) {
      handleError(error);
    }
  };

  const requestRefund = async () => {
    try {
      const promise = writeContractAsync({
        address: NODE_JACKPOT_ADDRESS,
        abi: RAFFLE_ABI,
        functionName: 'request_refund',
      });

      toast.promise(promise, {
        loading: 'Processing tactical retreat (refund)...',
        success: 'Refund secured!',
        error: (err) => err.shortMessage || 'Failed to request refund',
      });

      return await promise;
    } catch (error) {
      handleError(error);
    }
  };

  return {
    enterRaffle,
    requestElimination,
    claimPrize,
    requestRefund,
    isPending,
    isConfirming,
    isSuccess,
  };
}

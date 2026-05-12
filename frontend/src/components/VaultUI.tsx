'use client';

import { useState, useEffect } from 'react';
import { formatEther } from 'viem';
import { useJackpotData } from '@/hooks/useJackpotData';
import { useRaffle } from '@/hooks/useRaffle';
import { Wallet, Clock, ArrowUpRight, Lock, Unlock, AlertTriangle, Loader2, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';

export function VaultUI() {
  const { pendingClaim, unlockTime } = useJackpotData();
  const { claimPrize, isPending, isConfirming } = useRaffle();
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  useEffect(() => {
    if (!unlockTime || unlockTime === 0n) {
      setTimeLeft(null);
      return;
    }

    const timer = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const diff = Number(unlockTime) - now;
      if (diff <= 0) {
        setTimeLeft(0);
        clearInterval(timer);
      } else {
        setTimeLeft(diff);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [unlockTime]);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const hasBalance = pendingClaim && pendingClaim > 0n;
  const isLocked = timeLeft !== null && timeLeft > 0;

  return (
    <div className="glass-card border-white/5 overflow-hidden">
      <div className="p-5 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald/10 rounded-lg">
            <Wallet className="w-4 h-4 text-emerald" />
          </div>
          <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-zinc-300">Earnings Vault</h2>
        </div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald/60" />
          <span className="text-[9px] text-zinc-500 font-mono uppercase tracking-tighter">Pull-Payment Protocol</span>
        </div>
      </div>

      <div className="p-8 space-y-8">
        <div className="flex flex-col items-center justify-center space-y-3">
          <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-[0.3em]">Vault Liquidity</p>
          <div className="flex items-baseline gap-2">
            <span className={clsx(
              "text-6xl font-mono font-bold tracking-tighter transition-colors duration-500",
              hasBalance ? "aurora-text" : "text-zinc-800"
            )}>
              {hasBalance ? formatEther(pendingClaim) : '0.000'}
            </span>
            <span className="text-sm text-zinc-600 font-mono">ETH</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 space-y-2 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
              <Clock className="w-8 h-8 text-white" />
            </div>
            <div className="flex items-center gap-2 text-zinc-500">
              <span className="text-[9px] font-mono uppercase tracking-widest">Vesting</span>
            </div>
            <p className="text-lg font-mono font-bold text-zinc-200">
              {isLocked ? formatTime(timeLeft!) : (hasBalance ? 'UNLOCKED' : '--:--:--')}
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 space-y-2 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
              {isLocked ? <Lock className="w-8 h-8 text-white" /> : <Unlock className="w-8 h-8 text-white" />}
            </div>
            <div className="flex items-center gap-2 text-zinc-500">
              <span className="text-[9px] font-mono uppercase tracking-widest">Status</span>
            </div>
            <p className={clsx(
              "text-lg font-mono font-bold uppercase",
              isLocked ? "text-red-400/80" : (hasBalance ? "text-emerald" : "text-zinc-700")
            )}>
              {isLocked ? 'Locked' : (hasBalance ? 'Available' : 'Empty')}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => claimPrize()}
            disabled={!hasBalance || isLocked || isPending || isConfirming}
            className={clsx(
              "w-full py-4 rounded-2xl font-bold uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 relative overflow-hidden",
              "bg-transparent border border-emerald/30 text-emerald hover:bg-emerald/5 active:scale-[0.98]",
              "disabled:opacity-20 disabled:cursor-not-allowed disabled:hover:bg-transparent"
            )}
          >
            {isPending || isConfirming ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUpRight className="w-5 h-5" />}
            <span className="text-xs">Withdraw Loot</span>
          </button>

          <div className="p-4 bg-violet-aurora/[0.03] border border-violet-aurora/10 rounded-2xl flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-violet-aurora/60 mt-0.5 shrink-0" />
            <p className="text-[10px] text-zinc-500 leading-relaxed font-mono">
              The Great Hall requires manual collection of spoils. Winnings are vested for security to prevent rapid drainage.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


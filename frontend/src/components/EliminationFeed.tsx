'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useJackpotData } from '@/hooks/useJackpotData';
import { useWatchContractEvent } from 'wagmi';
import { RAFFLE_ABI, NODE_JACKPOT_ADDRESS } from '@/lib/contracts';
import { Skull, Loader2, Zap, Swords } from 'lucide-react';

type EliminationEvent = {
  loser: string;
  remaining: bigint;
  timestamp: number;
};

export function EliminationFeed() {
  const { raffleState, activeVikings, totalPlayers } = useJackpotData();
  const [events, setEvents] = useState<EliminationEvent[]>([]);

  // Watch for VikingEliminated events
  useWatchContractEvent({
    address: NODE_JACKPOT_ADDRESS,
    abi: RAFFLE_ABI,
    eventName: 'VikingEliminated',
    onLogs(logs) {
      const newEvents = logs.map((l) => {
        const log = l as unknown as { args: { loser: string; remaining: bigint } };
        const args = log.args;
        return {
          loser: args.loser,
          remaining: args.remaining,
          timestamp: Date.now(),
        };
      });
      setEvents(prev => [...newEvents, ...prev].slice(0, 10));
    },
  });

  const isCalculating = raffleState === 2n; // CALCULATING

  return (
    <div className="glass-card flex flex-col h-[500px] border-white/5 shadow-2xl">
      <div className="p-5 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-red-500/10 rounded-md">
            <Swords className="w-4 h-4 text-red-400" />
          </div>
          <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-zinc-300">Elimination Feed</h2>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono">
          <div className="flex flex-col items-end">
            <span className="text-zinc-500 uppercase tracking-tighter">Survivors</span>
            <span className="text-emerald font-bold">{activeVikings?.toString() || '0'}<span className="text-zinc-600 mx-1">/</span>{totalPlayers?.toString() || '0'}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
        <AnimatePresence mode="popLayout">
          {isCalculating && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="p-4 rounded-xl bg-emerald/5 border border-emerald/20 flex items-center gap-4 relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-emerald/0 via-emerald/[0.05] to-emerald/0 animate-[shimmer_2s_infinite]" />
              <div className="relative">
                <Loader2 className="w-6 h-6 text-emerald animate-spin" />
                <Zap className="w-3 h-3 text-emerald absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
              </div>
              <div className="relative z-10">
                <h3 className="text-[10px] font-bold text-emerald uppercase tracking-widest">VRF Oracle Active</h3>
                <p className="text-[9px] text-emerald/60 font-mono uppercase">Deciding Fates in Valhalla...</p>
              </div>
            </motion.div>
          )}

          {events.length === 0 && !isCalculating && (
            <div className="h-full flex flex-col items-center justify-center text-zinc-700 space-y-4 opacity-40">
              <div className="p-4 rounded-full border border-dashed border-zinc-800">
                <Skull className="w-8 h-8" />
              </div>
              <p className="text-[10px] font-mono uppercase tracking-[0.3em]">Battlefield Quiet</p>
            </div>
          )}

          {events.map((event) => (
            <motion.div
              key={`${event.loser}-${event.timestamp}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="p-3 border border-white/5 rounded-xl bg-white/[0.01] hover:bg-white/[0.03] transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-red-500/5 border border-red-500/10 flex items-center justify-center group-hover:border-red-500/30 transition-colors">
                    <Skull className="w-4 h-4 text-red-500/60 group-hover:text-red-500 transition-colors" />
                  </div>
                  <div>
                    <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-tighter mb-0.5">Fallen Warrior</p>
                    <p className="text-xs font-mono text-zinc-400 group-hover:text-zinc-200 transition-colors">
                      {event.loser.slice(0, 8)}...{event.loser.slice(-6)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-tighter mb-0.5">Remaining</p>
                  <p className="text-xs font-mono text-emerald font-bold">{event.remaining.toString()}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      
      <div className="p-4 bg-black/20 border-t border-white/5">
        <div className="flex items-center gap-3 text-[9px] text-zinc-600 font-mono uppercase tracking-widest">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald"></span>
          </div>
          <span>Synchronized with Chainlink Node</span>
        </div>
      </div>
    </div>
  );
}


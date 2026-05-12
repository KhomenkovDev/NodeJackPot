'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { formatEther } from 'viem';
import { useJackpotData } from '@/hooks/useJackpotData';
import { useRaffle } from '@/hooks/useRaffle';
import { useAccount } from 'wagmi';
import { Calculator, Info, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';

export function QuadraticEntry() {
  const { address } = useAccount();
  const { entranceFee, playerProfile } = useJackpotData();
  const { enterRaffle, isPending, isConfirming } = useRaffle();

  const currentTickets = playerProfile?.[0] || 0n;
  const nextTicketIndex = currentTickets + 1n;
  
  const nextTicketCost = useMemo(() => {
    if (!entranceFee) return 0n;
    return (nextTicketIndex ** 2n) * entranceFee;
  }, [nextTicketIndex, entranceFee]);

  const handleEnter = () => {
    enterRaffle(nextTicketCost);
  };

  // Generate curve points for SVG
  const curvePoints = useMemo(() => {
    const points = [];
    const maxTickets = Number(currentTickets) + 5;
    for (let i = 0; i <= maxTickets; i++) {
      const x = (i / maxTickets) * 100;
      const y = 100 - (Math.pow(i, 2) / Math.pow(maxTickets, 2)) * 80;
      points.push(`${x},${y}`);
    }
    return points.join(' ');
  }, [currentTickets]);

  const userX = useMemo(() => {
    const maxTickets = Number(currentTickets) + 5;
    return (Number(currentTickets) / maxTickets) * 100;
  }, [currentTickets]);

  const userY = useMemo(() => {
    const maxTickets = Number(currentTickets) + 5;
    return 100 - (Math.pow(Number(currentTickets), 2) / Math.pow(maxTickets, 2)) * 80;
  }, [currentTickets]);

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border-emerald/10">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald/10 rounded-lg">
              <Calculator className="w-5 h-5 text-emerald" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Quadratic Entry</h2>
              <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest">Entry Phase Active</p>
            </div>
          </div>
          <div className="px-3 py-1 bg-emerald/5 border border-emerald/10 rounded-full text-[10px] text-emerald uppercase font-mono tracking-tighter">
            Cost = T² × Base
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          <div className="space-y-6">
            <div className="relative p-6 rounded-2xl bg-black/40 border border-white/5 overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <TrendingUp className="w-12 h-12 text-emerald" />
              </div>
              <label className="block text-[10px] uppercase text-zinc-500 mb-2 font-mono tracking-widest">Current Standing</label>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-mono font-bold aurora-text">{currentTickets.toString()}</span>
                <span className="text-xs text-zinc-400 font-mono uppercase">Tickets</span>
              </div>
              
              <div className="mt-6 pt-6 border-t border-white/5 space-y-4">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-zinc-400 font-medium">Next Ticket Cost</span>
                  <div className="text-right">
                    <span className="font-mono text-emerald text-lg font-bold">
                      {entranceFee ? formatEther(nextTicketCost) : '0.00'}
                    </span>
                    <span className="ml-1 text-[10px] text-zinc-500 font-mono">ETH</span>
                  </div>
                </div>
                
                <button
                  onClick={handleEnter}
                  disabled={!address || isPending || isConfirming}
                  className={clsx(
                    "w-full py-4 rounded-xl font-bold uppercase tracking-widest transition-all relative overflow-hidden group/btn",
                    "bg-emerald text-black hover:shadow-[0_0_20px_rgba(0,255,187,0.4)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none",
                    (isPending || isConfirming) && "animate-pulse"
                  )}
                >
                  <span className="relative z-10 flex items-center justify-center gap-2">
                    {isPending || isConfirming ? 'Forging Ticket...' : (
                      <>
                        Buy Next Ticket
                        <motion.span
                          animate={{ x: [0, 4, 0] }}
                          transition={{ repeat: Infinity, duration: 1.5 }}
                        >
                          →
                        </motion.span>
                      </>
                    )}
                  </span>
                </button>
              </div>
            </div>
          </div>

          <div className="flex flex-col space-y-6">
            <div className="relative h-48 w-full glass-card p-4 flex flex-col justify-between border-white/5">
              <div className="absolute top-4 left-4 z-10">
                <h3 className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Cost Curve</h3>
              </div>
              
              <svg viewBox="0 0 100 100" className="w-full h-full mt-4 overflow-visible">
                {/* Grid Lines */}
                <line x1="0" y1="100" x2="100" y2="100" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
                <line x1="0" y1="20" x2="100" y2="20" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
                
                {/* The Curve */}
                <motion.polyline
                  points={curvePoints}
                  fill="none"
                  stroke="url(#aurora-gradient)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 1.5, ease: "easeOut" }}
                />
                
                {/* User Position */}
                <motion.circle
                  cx={userX}
                  cy={userY}
                  r="3"
                  className="fill-emerald"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 1, type: "spring" }}
                >
                  <animate attributeName="r" values="3;5;3" dur="2s" repeatCount="indefinite" />
                </motion.circle>
                
                <defs>
                  <linearGradient id="aurora-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#00FFBB" />
                    <stop offset="100%" stopColor="#8B5CF6" />
                  </linearGradient>
                </defs>
              </svg>
              
              <div className="flex justify-between text-[8px] font-mono text-zinc-600 uppercase mt-2">
                <span>0 Tickets</span>
                <span>Max Capacity</span>
              </div>
            </div>

            <div className="p-4 border border-white/5 rounded-2xl bg-white/[0.02]">
              <div className="flex items-start gap-3">
                <Info className="w-4 h-4 text-violet-aurora mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">Equitable Scaling</h3>
                  <p className="text-[10px] text-zinc-500 leading-relaxed">
                    Cost scales quadratically to prevent &quot;whale&quot; domination. Each subsequent ticket requires a larger sacrifice to the gods, maintaining a fair battlefield for all Vikings.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


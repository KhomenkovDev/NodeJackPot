'use client';

import { ConnectKitButton } from 'connectkit';
import { QuadraticEntry } from '@/components/QuadraticEntry';
import { EliminationFeed } from '@/components/EliminationFeed';
import { VaultUI } from '@/components/VaultUI';
import { useJackpotData } from '@/hooks/useJackpotData';
import { NODE_JACKPOT_ADDRESS } from '@/lib/contracts';
import { Shield, ExternalLink, Info, Zap, Swords, Anchor, Cpu } from 'lucide-react';
import { formatEther } from 'viem';
import { motion } from 'framer-motion';
import Image from 'next/image';

export default function Home() {
  const { potSize, roundNumber } = useJackpotData();

  return (
    <main className="max-w-7xl mx-auto px-6 py-12 space-y-12 relative">
      {/* Decorative Aurora Background Elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald/10 blur-[120px] rounded-full -z-10 animate-pulse" />
      <div className="absolute top-1/2 right-1/4 w-64 h-64 bg-violet-aurora/10 blur-[100px] rounded-full -z-10" />

      {/* Header */}
      <header className="flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="space-y-3 group cursor-default">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Swords className="w-10 h-10 text-emerald" />
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="absolute -inset-2 border border-emerald/20 border-dashed rounded-full"
              />
            </div>
            <div>
              <h1 className="text-4xl font-black uppercase tracking-tighter italic bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
                NodeJackPot
              </h1>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald animate-pulse" />
                <p className="text-zinc-500 font-mono text-[10px] uppercase tracking-[0.3em]">
                  Cyber-Nordic Elimination Protocol
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest text-right">Network Status</span>
            <span className="text-[10px] font-mono text-emerald uppercase tracking-widest text-right font-bold">Arbitrum Sepolia Live</span>
          </div>
          <ConnectKitButton.Custom>
            {({ isConnected, show, truncatedAddress, ensName }) => {
              return (
                <button
                  onClick={show}
                  className="px-6 py-3 bg-zinc-900 border border-white/10 rounded-2xl hover:border-emerald/40 hover:bg-zinc-800 transition-all font-mono text-xs uppercase tracking-widest group"
                >
                  <span className="flex items-center gap-2">
                    <div className={isConnected ? "text-emerald" : "text-zinc-500"}>
                      <Cpu className="w-4 h-4" />
                    </div>
                    {isConnected ? (ensName ?? truncatedAddress) : "Awaken Viking"}
                  </span>
                </button>
              );
            }}
          </ConnectKitButton.Custom>
        </div>
      </header>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: 'Valhalla Prize Pool', value: potSize ? `${formatEther(potSize)} ETH` : '0.00 ETH', icon: Zap, color: 'text-emerald', sub: 'Accumulated Loot' },
          { label: 'Battle Round', value: roundNumber?.toString() || '1', icon: Anchor, color: 'text-violet-aurora', sub: 'Current Conflict' },
          { label: 'Oracle Integrity', value: 'VERIFIED', icon: Shield, color: 'text-slate-nordic', sub: 'Chainlink VRF 2.5' },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-card p-6 flex items-center justify-between group relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.01] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="space-y-1 relative z-10">
              <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-[0.2em]">{stat.label}</p>
              <p className={`text-2xl font-mono font-bold ${stat.color}`}>{stat.value}</p>
              <p className="text-[9px] text-zinc-600 font-mono uppercase italic">{stat.sub}</p>
            </div>
            <stat.icon className={`w-10 h-10 ${stat.color} opacity-10 group-hover:opacity-30 group-hover:scale-110 transition-all duration-500 relative z-10`} />
          </motion.div>
        ))}
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-8 space-y-10">
          <QuadraticEntry />
          
          {/* Architecture Details */}
          <div className="glass-card border-white/5 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-[0.03] -rotate-12">
              <Shield className="w-48 h-48" />
            </div>
            <div className="p-8 space-y-8 relative z-10">
              <div className="flex items-center gap-4 border-b border-white/5 pb-6">
                <div className="p-2 bg-violet-aurora/10 rounded-lg">
                  <Shield className="w-5 h-5 text-violet-aurora" />
                </div>
                <div>
                  <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-zinc-200">Protocol Architecture</h2>
                  <p className="text-[10px] text-zinc-500 font-mono uppercase">Immutable Security Constraints</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald" />
                      <h4 className="text-[11px] font-bold uppercase text-zinc-300 tracking-wider">Provable Randomness</h4>
                    </div>
                    <p className="text-xs text-zinc-500 leading-relaxed font-medium">
                      Powered by Chainlink VRF 2.5. Every elimination is mathematically derived from on-chain entropy, ensuring no participant or developer can influence the battle&apos;s outcome.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald" />
                      <h4 className="text-[11px] font-bold uppercase text-zinc-300 tracking-wider">Vesting Protection</h4>
                    </div>
                    <p className="text-xs text-zinc-500 leading-relaxed font-medium">
                      A multi-hour vesting period is enforced on all winnings. This tactical delay prevents flash-loan attacks and ensures protocol stability during high-volatility events.
                    </p>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="p-5 bg-black/40 border border-white/5 rounded-2xl space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">Viking Registry</span>
                      <a 
                        href={`https://sepolia.arbiscan.io/address/${NODE_JACKPOT_ADDRESS}`}
                        target="_blank"
                        className="text-[9px] font-mono text-emerald flex items-center gap-1 hover:text-white transition-colors"
                      >
                        EXPLORE ARBISCAN <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5 font-mono text-[10px] break-all text-zinc-400">
                      {NODE_JACKPOT_ADDRESS}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-4 bg-emerald/5 border border-emerald/10 rounded-2xl">
                    <Info className="w-4 h-4 text-emerald" />
                    <span className="text-[9px] font-mono text-emerald/80 uppercase tracking-tighter">
                      Verified Vyper 0.4.3 • Open Source Protocol
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-4 space-y-10">
          <EliminationFeed />
          <VaultUI />
        </div>
      </div>

      {/* Footer */}
      <footer className="pt-16 pb-12 border-t border-white/5 text-center space-y-6">
        <div className="flex items-center justify-center gap-8 opacity-20 grayscale hover:grayscale-0 hover:opacity-100 transition-all duration-700">
          <Image src="https://cryptologos.cc/logos/chainlink-link-logo.png" width={20} height={20} className="h-5 w-auto" alt="Chainlink" />
          <Image src="https://cryptologos.cc/logos/arbitrum-arb-logo.png" width={20} height={20} className="h-5 w-auto" alt="Arbitrum" />
          <div className="h-4 w-px bg-zinc-800 mx-2" />
          <span className="font-mono text-[10px] uppercase tracking-[0.5em] text-zinc-400">KHOMDEV PROTOCOL</span>
        </div>
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest">
            Handcrafted with Viking Precision & Vyper Architecture
          </p>
          <p className="text-[9px] font-mono text-zinc-700 uppercase">
            &copy; 2026 NodeJackPot Elimination Engine
          </p>
        </div>
      </footer>
    </main>
  );
}


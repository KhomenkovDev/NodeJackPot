'use client';

import { WagmiProvider, createConfig } from 'wagmi';
import { arbitrumSepolia } from 'wagmi/chains';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectKitProvider, getDefaultConfig } from 'connectkit';
import { ReactNode, useState } from 'react';

const config = createConfig(
  getDefaultConfig({
    // Your WalletConnect Project ID
    walletConnectProjectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || 'demo',
    chains: [arbitrumSepolia],
    appName: 'NodeJackPot',
    appDescription: 'Secure Quadratic Elimination Raffle',
    appUrl: 'https://nodejackpot.khomdev.com',
    appIcon: 'https://nodejackpot.khomdev.com/icon.png',
  })
);

export function Web3Provider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <ConnectKitProvider mode="dark">
          {children}
        </ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

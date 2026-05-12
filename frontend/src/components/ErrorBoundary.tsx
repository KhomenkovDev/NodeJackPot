'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#050505] text-white p-6">
          <div className="glass-card p-8 max-w-md w-full text-center space-y-4">
            <h2 className="text-2xl font-bold aurora-text">Something went wrong</h2>
            <p className="text-zinc-400 text-sm">
              The shield wall has been breached. Please refresh the page or contact the builders.
            </p>
            <pre className="text-xs bg-black/50 p-4 rounded text-emerald/70 overflow-auto text-left max-h-32">
              {this.state.error?.message}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-3 bg-emerald/10 border border-emerald/20 hover:bg-emerald/20 text-emerald rounded-xl transition-all font-semibold"
            >
              Refresh Shields
            </button>
          </div>
        </div>
      );
    }

    return this.children;
  }
}

export default ErrorBoundary;

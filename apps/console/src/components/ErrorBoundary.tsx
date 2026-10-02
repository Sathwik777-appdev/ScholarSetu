import { Component, type ErrorInfo, type ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';

/** Last line of defence: a crash in one screen shows this instead of a blank page. No details are shown to users. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Console crashed', error.message, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="grid min-h-dvh place-items-center px-6">
        <div className="card max-w-md p-8 text-center">
          <div className="tricolour mx-auto mb-6 w-16 rounded-full" />
          <h1 className="text-xl font-semibold text-slate-900">Something went wrong</h1>
          <p className="mt-2 text-[15px] leading-6 text-slate-500">
            This page could not be shown. Your work is safe: nothing was changed. Reload to try again.</p>
          <button onClick={() => window.location.reload()} className="btn btn-primary mt-6">
            <RefreshCw className="h-4 w-4" /> Reload</button>
        </div>
      </div>
    );
  }
}

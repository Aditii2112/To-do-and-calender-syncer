interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <header className="bg-white/80 backdrop-blur-sm border-b border-oasis-200/60 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div>
          <h1 className="text-xl font-bold text-oasis-800 tracking-tight">
            🌴 Oasis OS
          </h1>
          <p className="text-xs text-oasis-500 -mt-0.5">
            Multi-Agent Calendar Assistant
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Connected
          </span>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-4">
        {children}
      </main>
    </div>
  );
}

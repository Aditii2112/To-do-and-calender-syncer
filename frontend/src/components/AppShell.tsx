import './AppShell.css';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <h1 className="app-shell__title">📅 Oasis OS</h1>
        <p className="app-shell__subtitle">Multi-Agent Calendar Assistant</p>
      </header>
      <main className="app-shell__main">
        {children}
      </main>
    </div>
  );
}

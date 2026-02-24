import { AppShell } from './components/AppShell'
import { ChatPane } from './components/ChatPane'
import './App.css'

function App() {
  return (
    <AppShell>
      <div className="chat-container">
        <ChatPane />
      </div>
    </AppShell>
  )
}

export default App

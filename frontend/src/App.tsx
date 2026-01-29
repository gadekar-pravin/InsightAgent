/**
 * Main App component for InsightAgent.
 */

import { useEffect } from 'react';
import { ChatProvider, useChat } from './context/ChatContext';
import { Header, ChatArea, ReasoningPanel } from './components';

function AppContent() {
  const {
    messages,
    suggestedFollowups,
    isLoading,
    currentReasoningTraces,
    hasMemory,
    initSession,
    sendChatMessage,
    error,
  } = useChat();

  // Initialize session on mount
  useEffect(() => {
    initSession();
  }, [initSession]);

  // Count saved findings for header badge
  const memorySavedCount = 0; // TODO: Track from memory events

  return (
    <div className="flex h-screen overflow-hidden bg-background-light dark:bg-background-dark text-[#0d141b] dark:text-slate-50 font-display">
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header hasMemory={hasMemory} memorySavedCount={memorySavedCount} />

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 px-6 py-3 text-red-700 dark:text-red-400 text-sm">
            <span className="material-symbols-outlined text-sm mr-2 align-middle">
              error
            </span>
            {error}
          </div>
        )}

        {/* Main content area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat area (2/3 on desktop) */}
          <div className="w-full lg:w-2/3 flex">
            <ChatArea
              messages={messages}
              suggestedFollowups={suggestedFollowups}
              isLoading={isLoading}
              onSendMessage={sendChatMessage}
            />
          </div>

          {/* Reasoning panel (1/3 on desktop, hidden on mobile) */}
          <div className="hidden lg:flex lg:w-1/3">
            <ReasoningPanel
              traces={currentReasoningTraces}
              isProcessing={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <ChatProvider>
      <AppContent />
    </ChatProvider>
  );
}

export default App;

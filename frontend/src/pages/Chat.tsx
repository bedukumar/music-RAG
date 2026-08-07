import React, { useState, useEffect } from 'react';
import ChatSidebar from '../components/chat/ChatSidebar';
import ChatWindow from '../components/chat/ChatWindow';
import { ChatAPI } from '../api/client';
import './Chat.css';

interface ConversationInfo {
  id: string;
  title: string;
  updatedAt: string;
}

const Chat: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Load conversations from local storage
  useEffect(() => {
    const saved = localStorage.getItem('ragpipe_conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConversations(parsed);
      } catch (e) {
        console.error('Failed to parse conversations', e);
      }
    }
  }, []);

  const saveConversations = (convos: ConversationInfo[]) => {
    setConversations(convos);
    localStorage.setItem('ragpipe_conversations', JSON.stringify(convos));
  };

  const handleNewChat = async () => {
    try {
      const conv = await ChatAPI.createConversation({ title: 'New Conversation' });
      const info: ConversationInfo = {
        id: conv.id,
        title: conv.title,
        updatedAt: conv.created_at,
      };
      saveConversations([info, ...conversations]);
      setActiveConversationId(info.id);
    } catch (err) {
      console.error('Error creating chat:', err);
    }
  };

  const handleDeleteChat = async (id: string) => {
    try {
      await ChatAPI.deleteConversation(id);
      const filtered = conversations.filter(c => c.id !== id);
      saveConversations(filtered);
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
    } catch (err) {
      console.error('Error deleting chat:', err);
    }
  };


  const handleUpdateTitle = (id: string, newTitle: string) => {
    setConversations(prev => {
      const updated = prev.map(c => c.id === id ? { ...c, title: newTitle } : c);
      localStorage.setItem('ragpipe_conversations', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <div className={`chat-layout ${!isSidebarOpen ? 'sidebar-collapsed' : ''} ${!activeConversationId ? 'chat-layout-empty' : ''}`}>
      <ChatSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={setActiveConversationId}
        onNewChat={handleNewChat}
        onDelete={handleDeleteChat}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />
      <div className="chat-main">
        {activeConversationId ? (
          <ChatWindow
            conversationId={activeConversationId}
            onUpdateTitle={(title) => handleUpdateTitle(activeConversationId, title)}
          />
        ) : (
          <div className="empty-state">
            <div className="badge-pill">AI-Powered Music Intelligence</div>
            <h1 className="empty-heading">Talk to Your Music Knowledge Base</h1>
            <p className="empty-subtitle">Search. Analyze. Discover.</p>
            <button className="cta-button" onClick={handleNewChat}>Start a Conversation <svg className="cta-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg></button>
            <div className="capability-chips">
              <div className="chip">
                <svg className="chip-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M14 10l-4 4m0-4l4 4"/></svg>
                Semantic Search
              </div>
              <div className="chip">
                <svg className="chip-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"/><polygon points="9 18 5 22 5 9 9 5"/></svg>
                Audio Retrieval
              </div>
              <div className="chip">
                <svg className="chip-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/></svg>
                Natural Language Queries
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;

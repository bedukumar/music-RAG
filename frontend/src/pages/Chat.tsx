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
    <div className="chat-layout">
      <ChatSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={setActiveConversationId}
        onNewChat={handleNewChat}
        onDelete={handleDeleteChat}
      />
      <div className="chat-main">
        {activeConversationId ? (
          <ChatWindow
            conversationId={activeConversationId}
            onUpdateTitle={(title) => handleUpdateTitle(activeConversationId, title)}
          />
        ) : (
          <div className="chat-empty-state">
            <h2>Welcome to RagPipe Chat</h2>
            <p>Select a conversation or start a new one to begin.</p>
            <button className="primary-button" onClick={handleNewChat}>Start New Chat</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;

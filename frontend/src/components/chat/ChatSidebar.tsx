import React from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';

interface ConversationInfo {
  id: string;
  title: string;
  updatedAt: string;
}

interface ChatSidebarProps {
  conversations: ConversationInfo[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete
}) => {
  return (
    <div className="chat-sidebar">
      <div className="chat-sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={16} />
          New Chat
        </button>
      </div>
      <div className="chat-list">
        {conversations.map(conv => (
          <div
            key={conv.id}
            className={`chat-list-item ${activeId === conv.id ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <MessageSquare size={16} style={{ flexShrink: 0, opacity: 0.7 }} />
            <span className="chat-list-item-title">{conv.title || 'New Conversation'}</span>
            <button
              className="delete-btn"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
              title="Delete conversation"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatSidebar;

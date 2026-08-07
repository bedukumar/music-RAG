import React, { useState } from 'react';
import { MessageSquare, Trash2, PanelLeftClose, PanelLeftOpen, SquarePen } from 'lucide-react';

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
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  isSidebarOpen,
  onToggleSidebar
}) => {
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConfirmId(id);
  };

  const handleConfirm = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirmId) onDelete(confirmId);
    setConfirmId(null);
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmId(null);
  };

  return (
    <div className="chat-sidebar">
      <div className="chat-sidebar-header">
        <button className="icon-action-btn" onClick={onToggleSidebar} title={isSidebarOpen ? "Close sidebar" : "Open sidebar"}>
          {isSidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
        </button>
        <button className="icon-action-btn" onClick={onNewChat} title="New Chat">
          <SquarePen size={20} />
        </button>
      </div>
      <div className="chat-list">
        {!isSidebarOpen ? (
          <div className="collapsed-chat-group">
            <div className="collapsed-chat-icon-wrapper">
              <MessageSquare size={20} style={{ opacity: 0.7 }} />
            </div>
            <div className="collapsed-chat-popup">
              <div className="collapsed-popup-header">Recent Chats</div>
              {conversations.slice(0, 5).map(conv => (
                <div
                  key={conv.id}
                  className={`collapsed-popup-item ${activeId === conv.id ? 'active' : ''}`}
                  onClick={() => onSelect(conv.id)}
                >
                  <span className="collapsed-popup-title">{conv.title || 'New Conversation'}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          conversations.map(conv => (
            <div
              key={conv.id}
              className={`chat-list-item ${activeId === conv.id ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              {confirmId === conv.id ? (
                /* Inline confirmation row */
                <div className="delete-confirm" onClick={e => e.stopPropagation()}>
                  <span className="delete-confirm-label">Delete?</span>
                  <button className="delete-confirm-yes" onClick={handleConfirm}>Yes</button>
                  <button className="delete-confirm-no" onClick={handleCancel}>No</button>
                </div>
              ) : (
                <>
                  <MessageSquare size={16} style={{ flexShrink: 0, opacity: 0.7 }} />
                  <span className="chat-list-item-title">{conv.title || 'New Conversation'}</span>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteClick(e, conv.id)}
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;

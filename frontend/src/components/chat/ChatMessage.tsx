import React from 'react';

export interface Citation {
  media_id?: string;
  title?: string;
  chunk_id?: string;
  modality?: string;
  score?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  // Other fields like tool_calls can be added here
}

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        <div className="message-content">
          {message.content}
        </div>
        {message.citations && message.citations.length > 0 && (
          <div className="message-citations">
            <div style={{ marginBottom: '4px', fontWeight: 500, color: 'var(--text-2)' }}>Sources:</div>
            {message.citations.map((c, i) => (
              <span key={i} className="citation-item">
                {c.title || c.media_id || 'Unknown Source'}
                {c.score && ` (${(c.score * 100).toFixed(1)}%)`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;

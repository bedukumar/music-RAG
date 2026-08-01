import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Undo, Check } from 'lucide-react';

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
}

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onRewind?: (messageId: string, content: string) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isStreaming, onRewind }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        <div className={`message-content${isStreaming ? ' streaming' : ''}`}>
          {message.role === 'assistant' ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          ) : (
            message.content
          )}
          {isStreaming && <span className="streaming-cursor">▍</span>}
        </div>
        {message.role === 'user' && (
          <div className="message-actions">
            <button className="action-button" onClick={handleCopy} title="Copy message">
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
            {onRewind && (
              <button className="action-button" onClick={() => onRewind(message.id, message.content)} title="Rewind & Edit from here">
                <Undo size={14} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;

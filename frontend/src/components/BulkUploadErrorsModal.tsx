import React, { useState, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { BulkUploadAPI } from '../api/client';

interface BulkUploadErrorsModalProps {
  uploadId: string;
  onClose: () => void;
}

interface RowError {
  row_number: number;
  error_message: string;
}

export default function BulkUploadErrorsModal({ uploadId, onClose }: BulkUploadErrorsModalProps) {
  const [errors, setErrors] = useState<RowError[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    BulkUploadAPI.errors(uploadId, { limit: 100 })
      .then((data) => {
        if (isMounted) {
          setErrors(data.items || []);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load errors:', err);
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, [uploadId]);

  return (
    <div className="modal-overlay" style={overlayStyle}>
      <div className="modal-content" style={contentStyle}>
        <div style={headerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={18} color="var(--error)" />
            <h3 style={{ margin: 0, color: 'var(--text-1)' }}>Upload Errors</h3>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>
            <X size={16} />
          </button>
        </div>
        
        <div style={bodyStyle}>
          {loading ? (
            <p style={{ color: 'var(--text-2)' }}>Loading errors...</p>
          ) : errors.length === 0 ? (
            <p style={{ color: 'var(--text-2)' }}>No errors found.</p>
          ) : (
            <div style={errorListStyle}>
              {errors.map((err, idx) => (
                <div key={idx} style={errorItemStyle}>
                  <div style={rowBadgeStyle}>Row {err.row_number}</div>
                  <div style={errorMessageStyle}>{err.error_message}</div>
                </div>
              ))}
              {errors.length === 100 && (
                <div style={{ textAlign: 'center', padding: '8px', color: 'var(--text-2)', fontSize: '12px' }}>
                  Showing first 100 errors...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.5)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 1000,
  backdropFilter: 'blur(2px)',
};

const contentStyle: React.CSSProperties = {
  backgroundColor: 'var(--bg-2)',
  borderRadius: '8px',
  width: '100%',
  maxWidth: '500px',
  maxHeight: '80vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
  border: '1px solid var(--border)',
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px 20px',
  borderBottom: '1px solid var(--border)',
};

const closeBtnStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'var(--text-2)',
  cursor: 'pointer',
  padding: '4px',
  display: 'flex',
};

const bodyStyle: React.CSSProperties = {
  padding: '20px',
  overflowY: 'auto',
};

const errorListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const errorItemStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  padding: '12px',
  backgroundColor: 'var(--bg-1)',
  borderRadius: '6px',
  border: '1px solid var(--error)',
  borderLeft: '4px solid var(--error)',
};

const rowBadgeStyle: React.CSSProperties = {
  fontSize: '12px',
  fontWeight: 600,
  color: 'var(--text-2)',
};

const errorMessageStyle: React.CSSProperties = {
  fontSize: '13px',
  color: 'var(--error)',
  wordBreak: 'break-word',
};

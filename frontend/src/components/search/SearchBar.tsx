import { useState } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { useSearchStore } from '../../store/searchStore';

export default function SearchBar() {
  const { query, setQuery, startSearch, isSearching } = useSearchStore();
  const [localQuery, setLocalQuery] = useState(query);

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!localQuery.trim()) return;
    setQuery(localQuery);
    startSearch();
  };

  const handleClear = () => {
    setLocalQuery('');
    setQuery('');
  };

  return (
    <form onSubmit={handleSearch}>
      <div
        style={{
          display: 'flex',
          gap: 8,
          padding: '4px 4px 4px 14px',
          background: 'var(--bg-1)',
          border: '1px solid var(--border-2)',
          borderRadius: 'var(--r-3)',
          transition: 'border-color var(--t-fast)',
        }}
        onFocusCapture={e => {
          (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)';
        }}
        onBlurCapture={e => {
          (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-2)';
        }}
      >
        {/* Icon */}
        <Search size={15} color="var(--text-3)" style={{ flexShrink: 0, alignSelf: 'center' }} />

        {/* Input */}
        <input
          type="text"
          value={localQuery}
          onChange={e => setLocalQuery(e.target.value)}
          placeholder="Search audio, transcripts, and metadata..."
          style={{
            flex: 1,
            height: 40,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-1)',
            fontFamily: 'var(--font)',
            fontSize: 14,
            letterSpacing: '-0.01em',
          }}
        />

        {/* Clear button */}
        {localQuery && !isSearching && (
          <button
            type="button"
            onClick={handleClear}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 24,
              height: 24,
              alignSelf: 'center',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-3)',
              borderRadius: 'var(--r-1)',
              flexShrink: 0,
            }}
          >
            <X size={13} />
          </button>
        )}

        {/* Submit button */}
        <button
          type="submit"
          className="btn btn-primary"
          style={{ height: 40, padding: '0 20px', borderRadius: 6, flexShrink: 0 }}
          disabled={isSearching || !localQuery.trim()}
        >
          {isSearching ? (
            <>
              <Loader2 size={13} className="spin" />
              Searching
            </>
          ) : 'Search'}
        </button>
      </div>
    </form>
  );
}

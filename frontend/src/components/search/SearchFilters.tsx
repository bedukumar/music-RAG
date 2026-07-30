import { useSearchStore } from '../../store/searchStore';

export default function SearchFilters() {
  const { filters, setFilters } = useSearchStore();

  const handleChange = (key: string, value: string) => {
    setFilters({ [key]: value || undefined });
  };

  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {['artist', 'album', 'genre', 'year'].map(field => (
        <input
          key={field}
          type={field === 'year' ? 'number' : 'text'}
          placeholder={field.charAt(0).toUpperCase() + field.slice(1)}
          value={(filters as any)[field] || ''}
          onChange={e => handleChange(field, e.target.value)}
          className="input-field"
          style={{ width: 140, height: 28, fontSize: 12 }}
        />
      ))}
      <input
        type="text"
        placeholder="Tags (comma separated)"
        value={filters.tags?.join(', ') || ''}
        onChange={e => {
          const val = e.target.value;
          setFilters({ tags: val ? val.split(',').map(s => s.trim()).filter(Boolean) : undefined });
        }}
        className="input-field"
        style={{ width: 200, height: 28, fontSize: 12 }}
      />
    </div>
  );
}

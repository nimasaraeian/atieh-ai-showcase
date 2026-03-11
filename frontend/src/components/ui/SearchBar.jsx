import { Search } from 'lucide-react'
import { cn } from '../../utils/cn'

export function SearchBar({ value, onChange, onSearch, placeholder = 'Search...', className }) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onSearch?.()
      }}
      className={cn('flex gap-2', className)}
    >
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-slate-700 bg-slate-800/80 py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
        />
      </div>
      <button
        type="submit"
        className="rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400"
      >
        Search
      </button>
    </form>
  )
}

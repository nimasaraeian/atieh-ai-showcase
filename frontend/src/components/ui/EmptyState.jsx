import { FileQuestion } from 'lucide-react'

export function EmptyState({ icon: Icon = FileQuestion, title, message }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-slate-800/80 p-4">
        <Icon className="h-8 w-8 text-slate-500" />
      </div>
      <p className="mt-3 font-medium text-slate-300">{title}</p>
      {message && <p className="mt-1 text-sm text-slate-500">{message}</p>}
    </div>
  )
}

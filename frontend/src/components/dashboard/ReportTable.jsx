import { useTranslation } from 'react-i18next'
import { cn } from '../../utils/cn'

export function ReportTable({ columns, data, emptyMessage }) {
  const { t } = useTranslation()

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10 bg-slate-800/95 text-xs text-slate-400">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn('whitespace-nowrap px-4 py-3 text-start', col.numeric && 'text-end')}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {!data?.length ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500">
                {emptyMessage || t('empty')}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={row.id ?? i} className="border-t border-slate-800 hover:bg-slate-800/30">
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn('px-4 py-2.5 text-start text-slate-300', col.className, col.numeric && 'text-end')}
                  >
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

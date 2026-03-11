import { useState } from 'react'
import { PageHeader } from '../components/layout/PageHeader'
import { SectionCard } from '../components/ui/SectionCard'
import { StatCard } from '../components/ui/StatCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { MOCK_DOCTOR_SCHEDULE, MOCK_PATIENTS } from '../data/mockData'
import { Calendar, CheckCircle2, Clock, Users } from 'lucide-react'

export function DoctorPage() {
  const [schedule] = useState(MOCK_DOCTOR_SCHEDULE)
  const [patients] = useState(MOCK_PATIENTS)
  const completed = schedule.filter((s) => s.status === 'completed').length
  const pending = schedule.filter((s) => s.status !== 'completed').length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Doctor Panel"
        subtitle="Today's schedule, patient list, and treatment overview"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total Today" value={schedule.length} icon={Calendar} accent="cyan" />
        <StatCard title="Completed" value={completed} icon={CheckCircle2} accent="green" />
        <StatCard title="Pending" value={pending} icon={Clock} accent="amber" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Today's Schedule" subtitle="Your appointments for today">
          <div className="space-y-2">
            {schedule.map((s, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-800/30 p-3"
              >
                <div>
                  <span className="font-medium text-slate-200">{s.time}</span>
                  <span className="ml-3 text-slate-400">{s.patient}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{s.service}</span>
                  <StatusBadge status={s.status} />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Patient List" subtitle="Patients in your care">
          <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-800">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-900/95 text-left text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Record #</th>
                  <th className="px-4 py-3">Last Visit</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.record_no} className="border-t border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-2.5 font-medium text-slate-200">{p.patient_name}</td>
                    <td className="px-4 py-2.5 text-slate-400">{p.record_no}</td>
                    <td className="px-4 py-2.5 text-slate-400">{p.last_visit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Treatment Overview" subtitle="Current operational focus">
        <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-4">
          <p className="text-sm font-medium text-slate-200">Next patient</p>
          <p className="mt-1 text-slate-400">
            {schedule.find((s) => s.status === 'in_progress')?.patient ?? schedule.find((s) => s.status === 'pending')?.patient ?? '-'}
          </p>
          <div className="mt-4 h-20 rounded-lg border border-dashed border-slate-700 bg-slate-900/50 p-3 text-xs text-slate-500">
            Quick notes placeholder
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

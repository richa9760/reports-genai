import { useState } from 'react'
import ManagerReportsMonthly from './ManagerReportsMonthly'
import ManagerReportsQuarterly from './ManagerReportsQuarterly'

const TABS = [
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
]

export default function ManagerReports() {
  const [period, setPeriod] = useState('monthly')

  return (
    <section className="panel">
      <h2>Manager Reports</h2>

      <nav className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab ${period === tab.id ? 'tab--active' : ''}`}
            aria-current={period === tab.id ? 'page' : undefined}
            onClick={() => setPeriod(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {period === 'monthly' ? <ManagerReportsMonthly /> : <ManagerReportsQuarterly />}
    </section>
  )
}
import { ITEM_SECTIONS, MONTHS } from '../constants'

export default function ManagerReportDetail({ detail }) {
  if (!detail) return null
  return (
    <div className="manager-detail">
      <h3>
        {detail.employee_name} — {MONTHS[detail.month - 1] ?? detail.month} {detail.year}
      </h3>
      <p>
        <strong>Project:</strong> {detail.project_name} · <strong>Business Group:</strong>{' '}
        {detail.business_group}
      </p>
      <p className="detail__summary">{detail.summary || 'No summary provided.'}</p>
      {ITEM_SECTIONS.map((section) => {
        const entries = detail.items[section.type] ?? []
        return (
          <div key={section.type} className="detail__group">
            <h4 className="manager-detail__heading">{section.label}</h4>
            {entries.length === 0 ? (
              <p className="section__empty">No entries.</p>
            ) : (
              <ul className="detail__list">
                {entries.map((item) => (
                  <li key={item.id}>{item.content}</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
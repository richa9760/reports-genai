import { useEffect, useState } from 'react'
import {
  createReport,
  createReportItem,
  deleteReportItem,
  generateReportSummary,
  getReport,
  updateReport,
  updateReportItem,
} from '../api/reports'
import { ITEM_SECTIONS, MONTHS } from '../constants'
import { ErrorMessage, LoadingMessage, SuccessMessage } from './Feedback'
import ItemSections from './ItemSection'
import { countItems, emptyItemsByType, itemsFromReport } from './itemState'

const TYPES = ITEM_SECTIONS.map((section) => section.type)

function currentDefaults() {
  const now = new Date()
  return { month: String(now.getMonth() + 1), year: String(now.getFullYear()) }
}

function validate({ employeeName, projectName, businessGroup, month, year, itemCount }) {
  const errors = {}
  if (!employeeName.trim()) errors.employeeName = 'Employee Name is required.'
  if (!projectName.trim()) errors.projectName = 'Project Name is required.'
  if (!businessGroup.trim()) errors.businessGroup = 'Business Group is required.'
  if (!month) errors.month = 'Month is required.'
  if (!year) errors.year = 'Year is required.'
  if (itemCount === 0) errors.items = 'Add at least one report item before saving.'
  return errors
}

function toPayload(fields) {
  return {
    employee_name: fields.employeeName.trim(),
    project_name: fields.projectName.trim(),
    business_group: fields.businessGroup.trim(),
    month: Number(fields.month),
    year: Number(fields.year),
  }
}

function toGeneratePayload(fields, itemsByType) {
  const entries = (type) =>
    (itemsByType[type] ?? []).map((entry) => entry.content.trim()).filter(Boolean)

  return {
    ...toPayload(fields),
    tasks: entries('TASK'),
    achievements: entries('ACHIEVEMENT'),
    courses: entries('COURSE'),
    planned_holidays: entries('HOLIDAY'),
    ideas: entries('IDEA'),
  }
}

/** Creates a report then attaches its items, or updates an existing one. */
async function persist({ reportId, fields, itemsByType, originalItems }) {
  const payload = toPayload(fields)

  if (!reportId) {
    const report = await createReport({ ...payload, summary: fields.summary.trim() })

    for (const [type, items] of Object.entries(itemsByType)) {
      for (const item of items.filter((entry) => entry.content.trim())) {
        await createReportItem(report.id, { item_type: type, content: item.content.trim() })
      }
    }

    return report
  }

  const report = await updateReport(reportId, { ...payload, summary: fields.summary.trim() })

  for (const type of TYPES) {
    const current = (itemsByType[type] ?? []).filter((item) => item.content.trim())
    const previous = originalItems[type] ?? []
    const currentIds = new Set(current.map((item) => item.serverId).filter(Boolean))

    for (const item of previous) {
      if (!currentIds.has(item.serverId)) {
        await deleteReportItem(item.serverId)
      }
    }

    for (const item of current) {
      if (item.serverId === null) {
        await createReportItem(reportId, { item_type: type, content: item.content.trim() })
      } else {
        const before = previous.find((entry) => entry.serverId === item.serverId)
        if (before && before.content.trim() !== item.content.trim()) {
          await updateReportItem(item.serverId, { content: item.content.trim() })
        }
      }
    }
  }

  return report
}

export default function ReportForm({ reportId, onSaved, onCancel }) {
  const isEditing = Boolean(reportId)

  const [fields, setFields] = useState({
    employeeName: '',
    projectName: '',
    businessGroup: '',
    ...currentDefaults(),
    summary: '',
  })
  const [itemsByType, setItemsByType] = useState(() => emptyItemsByType(TYPES))
  const [originalItems, setOriginalItems] = useState({})

  const [loadState, setLoadState] = useState(isEditing ? 'loading' : 'ready')
  const [formErrors, setFormErrors] = useState({})
  const [submitState, setSubmitState] = useState('idle')
  const [submitError, setSubmitError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [generateState, setGenerateState] = useState('idle')
  const [generateError, setGenerateError] = useState('')

  useEffect(() => {
    if (!isEditing) return

    let active = true

    getReport(reportId)
      .then((report) => {
        if (!active) return
        const grouped = itemsFromReport(report.items)
        setFields({
          employeeName: report.employee_name ?? '',
          projectName: report.project_name ?? '',
          businessGroup: report.business_group ?? '',
          month: String(report.month),
          year: String(report.year),
          summary: report.summary ?? '',
        })
        setItemsByType({ ...emptyItemsByType(TYPES), ...grouped })
        setOriginalItems(grouped)
        setLoadState('ready')
      })
      .catch(() => {
        if (!active) return
        setLoadState('error')
      })

    return () => {
      active = false
    }
  }, [isEditing, reportId])

  function updateField(name, value) {
    setFields((previous) => ({ ...previous, [name]: value }))
    setFormErrors((previous) => ({ ...previous, [name]: undefined }))
  }

  function updateItems(type, items) {
    setItemsByType((previous) => ({ ...previous, [type]: items }))
    setFormErrors((previous) => ({ ...previous, items: undefined }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSuccessMessage('')
    setSubmitError('')

    const itemCount = countItems(itemsByType)
    const errors = validate({ ...fields, itemCount })
    setFormErrors(errors)

    if (Object.keys(errors).length > 0) return

    setSubmitState('saving')

    try {
      const report = await persist({
        reportId,
        fields,
        itemsByType,
        originalItems,
      })

      setSubmitState('idle')
      setSuccessMessage(`Report saved successfully${isEditing ? '' : ' — you can now view it under My Reports'}.`)

      if (isEditing) {
        const grouped = itemsFromReport({
          ...emptyItemsByType(TYPES),
          ...Object.fromEntries(
            Object.entries(itemsByType).map(([type, items]) => [
              type,
              items
                .filter((item) => item.content.trim())
                .map((item, index) => ({
                  id: item.serverId ?? `pending-${type}-${index}`,
                  content: item.content,
                })),
            ])
          ),
        })
        setItemsByType(grouped)
        setOriginalItems(grouped)
      } else {
        setFields({
          employeeName: '',
          projectName: '',
          businessGroup: '',
          ...currentDefaults(),
          summary: '',
        })
        setItemsByType(emptyItemsByType(TYPES))
      }

      onSaved?.(report)
    } catch (error) {
      setSubmitState('idle')
      setSubmitError(error.message || 'Unable to save the report. Please try again.')
    }
  }

  async function handleGenerate() {
    setSuccessMessage('')
    setGenerateError('')

    const itemCount = countItems(itemsByType)
    const errors = validate({ ...fields, itemCount })
    setFormErrors(errors)
    if (Object.keys(errors).length > 0) return

    if (
      fields.summary.trim() &&
      !window.confirm(
        'A summary already exists. Replace it with the AI-generated summary?'
      )
    ) {
      return
    }

    setGenerateState('generating')
    try {
      const payload = toGeneratePayload(fields, itemsByType)
      const { summary } = await generateReportSummary(payload)
      setFields((previous) => ({ ...previous, summary: summary ?? '' }))
      setGenerateState('idle')
    } catch (error) {
      setGenerateState('idle')
      setGenerateError(error.message || 'Unable to generate the summary. Please try again.')
    }
  }

  if (loadState === 'loading') return <LoadingMessage>Loading report...</LoadingMessage>
  if (loadState === 'error') return <ErrorMessage>Unable to load the report. Please try again.</ErrorMessage>

  const isSaving = submitState === 'saving'
  const isGenerating = generateState === 'generating'

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <h2>{isEditing ? 'Edit Monthly Report' : 'Create Monthly Report'}</h2>

      <div className="field-row">
        <div className="field">
          <label htmlFor="month">Month</label>
          <select
            id="month"
            value={fields.month}
            disabled={isSaving}
            onChange={(event) => updateField('month', event.target.value)}
          >
            {MONTHS.map((name, index) => (
              <option key={name} value={index + 1}>
                {name}
              </option>
            ))}
          </select>
          {formErrors.month && <p className="field__error">{formErrors.month}</p>}
        </div>

        <div className="field">
          <label htmlFor="year">Year</label>
          <input
            id="year"
            type="number"
            value={fields.year}
            disabled={isSaving}
            onChange={(event) => updateField('year', event.target.value)}
          />
          {formErrors.year && <p className="field__error">{formErrors.year}</p>}
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label htmlFor="employeeName">Employee Name</label>
          <input
            id="employeeName"
            type="text"
            value={fields.employeeName}
            disabled={isSaving}
            placeholder="e.g. Richa Verma"
            onChange={(event) => updateField('employeeName', event.target.value)}
          />
          {formErrors.employeeName && <p className="field__error">{formErrors.employeeName}</p>}
        </div>

        <div className="field">
          <label htmlFor="projectName">Project Name</label>
          <input
            id="projectName"
            type="text"
            value={fields.projectName}
            disabled={isSaving}
            placeholder="e.g. AI Automation"
            onChange={(event) => updateField('projectName', event.target.value)}
          />
          {formErrors.projectName && <p className="field__error">{formErrors.projectName}</p>}
        </div>

        <div className="field">
          <label htmlFor="businessGroup">Business Group</label>
          <input
            id="businessGroup"
            type="text"
            value={fields.businessGroup}
            disabled={isSaving}
            placeholder="e.g. Data Center"
            onChange={(event) => updateField('businessGroup', event.target.value)}
          />
          {formErrors.businessGroup && <p className="field__error">{formErrors.businessGroup}</p>}
        </div>
      </div>

      <ItemSections itemsByType={itemsByType} onChangeType={updateItems} disabled={isSaving} />

      <fieldset className="section" disabled={isSaving}>
        <legend className="section__legend">Summary</legend>
        <textarea
          rows={4}
          value={fields.summary}
          aria-label="Summary"
          placeholder="Describe your month"
          disabled={isGenerating}
          onChange={(event) => updateField('summary', event.target.value)}
        />
        <button
          type="button"
          className="button button--secondary"
          disabled={isSaving || isGenerating}
          onClick={handleGenerate}
        >
          {isGenerating ? 'Generating...' : 'Generate Summary with AI'}
        </button>
        {generateError && <ErrorMessage>{generateError}</ErrorMessage>}
      </fieldset>

      {formErrors.items && <p className="field__error">{formErrors.items}</p>}
      {submitError && <ErrorMessage>{submitError}</ErrorMessage>}
      {successMessage && <SuccessMessage>{successMessage}</SuccessMessage>}

      <div className="actions">
        <button type="submit" className="button" disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Report'}
        </button>
        {onCancel && (
          <button type="button" className="button button--secondary" onClick={onCancel} disabled={isSaving}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
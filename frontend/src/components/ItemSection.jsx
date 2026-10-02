import { ITEM_SECTIONS } from '../constants'

/**
 * Renders one repeatable section (tasks, achievements, courses, holidays, ideas).
 * Every section works on the same item shape, so there is a single code path.
 */
function ItemSection({ type, label, addLabel, items, onChange, disabled }) {
  function updateItem(index, content) {
    onChange(type, items.map((item, i) => (i === index ? { ...item, content } : item)))
  }

  function removeItem(index) {
    onChange(type, items.filter((_, i) => i !== index))
  }

  return (
    <fieldset className="section" disabled={disabled}>
      <legend className="section__legend">{label}</legend>

      {items.length === 0 && <p className="section__empty">No entries yet.</p>}

      {items.map((item, index) => (
        <div className="item-row" key={item.localId}>
          <input
            type="text"
            className="item-row__input"
            value={item.content}
            placeholder={`Enter ${label.toLowerCase()} entry`}
            aria-label={`${label} entry ${index + 1}`}
            onChange={(event) => updateItem(index, event.target.value)}
          />
          <button
            type="button"
            className="item-row__remove"
            aria-label={`Remove ${label} entry ${index + 1}`}
            onClick={() => removeItem(index)}
          >
            Remove
          </button>
        </div>
      ))}

      <button
        type="button"
        className="section__add"
        onClick={() =>
          onChange(type, [
            ...items,
            { localId: `new-${type}-${items.length}-${Date.now()}`, content: '', serverId: null },
          ])
        }
      >
        {addLabel}
      </button>
    </fieldset>
  )
}

export default function ItemSections({ itemsByType, onChangeType, disabled }) {
  return (
    <>
      {ITEM_SECTIONS.map((section) => (
        <ItemSection
          key={section.type}
          type={section.type}
          label={section.label}
          addLabel={section.addLabel}
          items={itemsByType[section.type] ?? []}
          onChange={onChangeType}
          disabled={disabled}
        />
      ))}
    </>
  )
}

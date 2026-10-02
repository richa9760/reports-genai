let nextLocalId = 0

/** Stable client-side key for an item row; `serverId` is null until saved. */
export function createLocalItem(content = '', serverId = null) {
  nextLocalId += 1
  return { localId: `item-${nextLocalId}`, content, serverId }
}

export function emptyItemsByType(types) {
  return Object.fromEntries(types.map((type) => [type, []]))
}

/** Converts the grouped `items` object from the detail endpoint into form state. */
export function itemsFromReport(groupedItems) {
  const result = {}

  for (const [type, items] of Object.entries(groupedItems ?? {})) {
    result[type] = items.map((item) => createLocalItem(item.content, item.id))
  }

  return result
}

export function countItems(itemsByType) {
  return Object.values(itemsByType).reduce(
    (total, items) => total + items.filter((item) => item.content.trim()).length,
    0
  )
}

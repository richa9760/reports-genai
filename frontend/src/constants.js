/** Item types supported by the backend `ReportItem.item_type` field. */
export const ITEM_SECTIONS = [
  { type: 'TASK', label: 'Tasks Completed', addLabel: '+ Add Task' },
  { type: 'ACHIEVEMENT', label: 'Achievements / Rewards', addLabel: '+ Add Achievement' },
  { type: 'COURSE', label: 'Courses Taken', addLabel: '+ Add Course' },
  { type: 'HOLIDAY', label: 'Planned Holidays', addLabel: '+ Add Holiday' },
  { type: 'IDEA', label: 'Ideas Submitted', addLabel: '+ Add Idea' },
]

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export const QUARTERS = [
  { value: 1, label: 'Q1' },
  { value: 2, label: 'Q2' },
  { value: 3, label: 'Q3' },
  { value: 4, label: 'Q4' },
]

export const QUARTER_MONTHS = {
  1: [1, 2, 3],
  2: [4, 5, 6],
  3: [7, 8, 9],
  4: [10, 11, 12],
}

export function yearOptions() {
  const current = new Date().getFullYear()
  const years = []
  for (let year = current - 9; year <= current; year += 1) years.push(year)
  return years
}

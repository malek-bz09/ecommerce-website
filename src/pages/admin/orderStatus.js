// Order statuses, in the order an order normally moves through them.
// The backend (TRANSITIONS in backend/app/admin.py) decides which moves are allowed.
export const STATUSES = {
  pending: { label: 'Pending', tone: 'warn' },
  confirmed: { label: 'Confirmed', tone: 'info' },
  delivered: { label: 'Delivered', tone: 'ok' },
  returned: { label: 'Returned', tone: 'bad' },
  cancelled: { label: 'Cancelled', tone: 'muted' },
}

// Button text for moving an order to each status, and what it does
export const ACTIONS = {
  confirmed: { label: 'Confirm sale', hint: 'Takes the items out of stock' },
  delivered: { label: 'Mark delivered', hint: 'The customer paid' },
  returned: { label: 'Mark returned', hint: 'Puts the items back in stock' },
  cancelled: { label: 'Cancel order', hint: 'Puts the items back in stock if confirmed' },
}

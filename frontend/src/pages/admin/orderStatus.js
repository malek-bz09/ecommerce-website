// Order statuses, in the order an order normally moves through them.
// Keep in sync with ORDER_STATUSES in backend/app/models/order.py, which also
// decides which moves are allowed (TRANSITIONS).
export const STATUSES = {
  pending: { label: 'Pending', tone: 'warn' },
  confirmed: { label: 'Confirmed', tone: 'info' },
  processing: { label: 'Processing', tone: 'info' },
  shipped: { label: 'Shipped', tone: 'info' },
  delivered: { label: 'Delivered', tone: 'ok' },
  returned: { label: 'Returned', tone: 'bad' },
  cancelled: { label: 'Cancelled', tone: 'muted' },
}

// Button text for moving an order to each status, and what it does.
// (Stock is set aside as soon as an order is placed.)
export const ACTIONS = {
  confirmed: { label: 'Confirm order', hint: 'You called the customer and they confirmed' },
  processing: { label: 'Start preparing', hint: 'The parcel is being packed' },
  shipped: { label: 'Mark shipped', hint: 'Handed to the delivery company' },
  delivered: { label: 'Mark delivered', hint: 'The customer paid' },
  returned: { label: 'Mark returned', hint: 'Puts the items back in stock' },
  cancelled: { label: 'Cancel order', hint: 'Puts the items back in stock' },
}

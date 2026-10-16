import { ApiError, apiFetch } from './api'

// Flat home-delivery fee, paid in cash with the order (the server uses the same value)
export const DELIVERY_FEE = 600

export class OrderError extends Error {
  constructor(message, { fieldErrors = null, cartChanged = false } = {}) {
    super(message)
    this.name = 'OrderError'
    this.fieldErrors = fieldErrors
    this.cartChanged = cartChanged
  }
}

// Sends the order to the backend, which re-checks everything and saves it as "pending"
// until an admin confirms the sale
export async function placeOrder({ customer, items }) {
  try {
    return await apiFetch('/orders', { method: 'POST', body: { customer, items } })
  } catch (error) {
    if (!(error instanceof ApiError)) throw error
    throw new OrderError(error.message, {
      fieldErrors: error.data?.fieldErrors ?? null,
      cartChanged: error.data?.cartChanged ?? false,
    })
  }
}

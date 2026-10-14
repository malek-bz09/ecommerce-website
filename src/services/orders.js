import { products } from '../data/products'
import { normalizePhone, validateCheckout } from '../utils/validateCheckout'
import { wilayas } from '../data/wilayas'

// Flat home-delivery fee, paid in cash with the order
export const DELIVERY_FEE = 600

const STORAGE_KEY = 'orders'

export class OrderError extends Error {
  constructor(message, { fieldErrors = null, cartChanged = false } = {}) {
    super(message)
    this.name = 'OrderError'
    this.fieldErrors = fieldErrors
    this.cartChanged = cartChanged
  }
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// Mock API: re-validates everything like a real server would, then "saves" the order.
// Replace the body with a fetch() to your backend when you have one.
export async function placeOrder({ customer, items }) {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new OrderError('You appear to be offline. Check your connection and try again.')
  }

  await delay(800)

  const fieldErrors = validateCheckout(customer)
  if (Object.keys(fieldErrors).length > 0) {
    throw new OrderError('Some of your details are invalid.', { fieldErrors })
  }

  if (!items.length) {
    throw new OrderError('Your cart is empty.', { cartChanged: true })
  }

  const lines = items.map(({ id, quantity }) => {
    const product = products.find((p) => p.id === id)
    if (!product) {
      throw new OrderError('An item in your cart is no longer available.', { cartChanged: true })
    }
    if (!Number.isInteger(quantity) || quantity < 1) {
      throw new OrderError(`Invalid quantity for ${product.name}.`, { cartChanged: true })
    }
    if (product.stock === 0) {
      throw new OrderError(`${product.name} is sold out. Please remove it from your cart.`, {
        cartChanged: true,
      })
    }
    if (quantity > product.stock) {
      throw new OrderError(`Only ${product.stock} of ${product.name} left in stock.`, {
        cartChanged: true,
      })
    }
    return { id, name: product.name, price: product.price, quantity }
  })

  const subtotal = lines.reduce((sum, line) => sum + line.price * line.quantity, 0)
  const order = {
    id: `ORD-${Date.now().toString(36).toUpperCase()}`,
    createdAt: new Date().toISOString(),
    paymentMethod: 'cod',
    customer: {
      fullName: customer.fullName.trim(),
      phone: normalizePhone(customer.phone),
      email: customer.email.trim().toLowerCase(),
      wilaya: wilayas.find((w) => w.code === customer.wilaya).name,
      commune: customer.commune.trim(),
      address: customer.address.trim(),
      notes: customer.notes.trim(),
    },
    lines,
    subtotal,
    deliveryFee: DELIVERY_FEE,
    total: subtotal + DELIVERY_FEE,
  }

  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? []
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...saved, order]))
  } catch {
    // Storage is only a stand-in for a backend; the order still succeeds without it
  }

  return order
}

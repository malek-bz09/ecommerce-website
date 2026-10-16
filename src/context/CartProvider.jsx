import { useEffect, useReducer } from 'react'
import { CartContext } from './cart'
import { useProducts } from './products'

const STORAGE_KEY = 'cart'


function cartReducer(items, action) {
  switch (action.type) {
    case 'add': {
      const existing = items.find((item) => item.id === action.id)
      if (existing) {
        return items.map((item) =>
          item.id === action.id
            ? { ...item, quantity: Math.min(action.stock, item.quantity + action.quantity) }
            : item,
        )
      }
      return [...items, { id: action.id, quantity: Math.min(action.stock, action.quantity) }]
    }
    case 'update':
      return items.map((item) =>
        item.id === action.id ? { ...item, quantity: action.quantity } : item,
      )
    case 'remove':
      return items.filter((item) => item.id !== action.id)
    case 'clear':
      return []
    default:
      throw new Error(`Unknown cart action: ${action.type}`)
  }
}

function loadCart() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

function CartProvider({ children }) {
  const [items, dispatch] = useReducer(cartReducer, undefined, loadCart)
  const { products } = useProducts()

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    } catch {
      // Storage can be unavailable (private mode); the cart still works in memory
    }
  }, [items])

  // Join cart items with their product, dropping any that no longer exist
  const lines = items
    .map((item) => ({ ...item, product: products.find((p) => p.id === item.id) }))
    .filter((line) => line.product)

  const count = lines.reduce((sum, line) => sum + line.quantity, 0)
  const subtotal = lines.reduce((sum, line) => sum + line.product.price * line.quantity, 0)

  const value = {
    lines,
    count,
    subtotal,
    addItem: (product, quantity = 1) =>
      dispatch({ type: 'add', id: product.id, quantity, stock: product.stock }),
    updateQuantity: (id, quantity) =>
      quantity < 1 ? dispatch({ type: 'remove', id }) : dispatch({ type: 'update', id, quantity }),
    removeItem: (id) => dispatch({ type: 'remove', id }),
    clearCart: () => dispatch({ type: 'clear' }),
  }

  return <CartContext value={value}>{children}</CartContext>
}

export default CartProvider

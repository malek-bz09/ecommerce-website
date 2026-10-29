import { useEffect, useState } from 'react'
import { ProductsContext } from './products'
import { apiFetch, fetchAllPages } from '../services/api'

// Loads the catalogue from the backend once, and shares it with every page
function ProductsProvider({ children }) {
  const [state, setState] = useState({ products: [], loading: true, error: null })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let ignore = false
    fetchAllPages(apiFetch, '/products').then(
      (products) => !ignore && setState({ products, loading: false, error: null }),
      (error) => !ignore && setState((s) => ({ ...s, loading: false, error: error.message })),
    )
    return () => {
      ignore = true
    }
  }, [version])

  const value = {
    ...state,
    // Fetch again, e.g. after an admin changes a product or stock
    reload: () => setVersion((v) => v + 1),
  }

  return <ProductsContext value={value}>{children}</ProductsContext>
}

export default ProductsProvider

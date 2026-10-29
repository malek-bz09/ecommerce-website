import { useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../../context/auth'
import { useProducts } from '../../context/products'
import { getCategoryName } from '../../data/products'
import { formatPrice } from '../../utils/formatPrice'
import { useAdminData } from './useAdminData'
import './AdminPages.css'

const LOW_STOCK = 3

function stockStatus({ stock, isAvailable }) {
  if (!isAvailable) return { label: 'Hidden', tone: 'muted' }
  if (stock === 0) return { label: 'Sold out', tone: 'bad' }
  if (stock <= LOW_STOCK) return { label: 'Low stock', tone: 'warn' }
  return { label: 'In stock', tone: 'ok' }
}

function AdminProductsPage() {
  const { authFetch } = useAuth()
  const catalog = useProducts()
  const { data: products, error, loading, reload } = useAdminData('/admin/products', { allPages: true })
  const [deletingId, setDeletingId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const handleDelete = async (product) => {
    if (!window.confirm(`Delete “${product.name}”? It will disappear from the shop.`)) return
    setDeletingId(product.id)
    setActionError(null)
    try {
      await authFetch(`/products/${product.id}`, { method: 'DELETE' })
      reload()
      catalog.reload()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section>
      <header className="admin-page-header">
        <div>
          <h1>Products</h1>
          {products && (
            <p>
              {products.length} products · {products.reduce((sum, p) => sum + p.stock, 0)} items
              in stock
            </p>
          )}
        </div>
        <Link to="/admin/products/new" className="admin-button">
          New product
        </Link>
      </header>

      {loading && <p className="admin-message">Loading products…</p>}
      {error && <p className="admin-alert">{error}</p>}
      {actionError && (
        <p className="admin-alert" role="alert">
          {actionError}
        </p>
      )}
      {products?.length === 0 && (
        <p className="admin-message">No products yet. Add your first one.</p>
      )}

      {products?.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th></th>
                <th>Product</th>
                <th>Category</th>
                <th className="is-number">Price</th>
                <th className="is-number">Quantity</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => {
                const status = stockStatus(product)
                return (
                  <tr key={product.id}>
                    <td>
                      <img className="admin-product-image" src={product.images[0]} alt="" />
                    </td>
                    <td>
                      <Link to={`/admin/products/${product.id}`} className="admin-row-link">
                        {product.name}
                      </Link>
                    </td>
                    <td>{getCategoryName(product.category)}</td>
                    <td className="is-number">
                      {formatPrice(product.price)}
                      {product.compareAtPrice && <small>was {formatPrice(product.compareAtPrice)}</small>}
                    </td>
                    <td className="is-number">{product.stock}</td>
                    <td>
                      <span className={`admin-status admin-status--${status.tone}`}>
                        {status.label}
                      </span>
                    </td>
                    <td>
                      <div className="admin-actions">
                        <Link to={`/admin/products/${product.id}`} className="admin-link">
                          Edit
                        </Link>
                        <button
                          type="button"
                          className="admin-link--danger"
                          disabled={deletingId === product.id}
                          onClick={() => handleDelete(product)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default AdminProductsPage

import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useAuth } from '../../context/auth'
import { useProducts } from '../../context/products'
import { formatPrice } from '../../utils/formatPrice'
import { formatDate } from './formatDate'
import { ACTIONS, STATUSES } from './orderStatus'
import StatusBadge from './StatusBadge'
import { useAdminData } from './useAdminData'
import './AdminPages.css'
import './AdminOrderPage.css'

function AdminOrderPage() {
  const { orderId } = useParams()
  const { authFetch } = useAuth()
  const catalog = useProducts()
  const { data: order, error, loading, reload } = useAdminData(`/admin/orders/${orderId}`)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const changeStatus = async (status) => {
    const { label, hint } = ACTIONS[status]
    if ((status === 'returned' || status === 'cancelled') && !window.confirm(`${label}? ${hint}.`)) {
      return
    }
    setBusy(true)
    setActionError(null)
    try {
      await authFetch(`/admin/orders/${orderId}/status`, { method: 'PATCH', body: { status } })
      reload()
      catalog.reload() // stock may have changed, so refresh the shop's copy too
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="admin-message">Loading order…</p>
  if (error) return <p className="admin-alert">{error}</p>

  const { customer, lines, history } = order

  return (
    <section>
      <Link to="/admin/orders" className="admin-back">
        ← All orders
      </Link>

      <header className="admin-page-header">
        <h1>
          Order {order.orderNumber} <StatusBadge status={order.status} />
        </h1>
        <p>Placed {formatDate(history.pending)}</p>
      </header>

      {order.nextStatuses.length > 0 && (
        <div className="order-actions">
          {order.nextStatuses.map((status, index) => (
            <button
              key={status}
              type="button"
              // The first next step is the usual one, so it gets the strong style
              className={`admin-button${index > 0 ? ' admin-button--secondary' : ''}`}
              disabled={busy}
              title={ACTIONS[status].hint}
              onClick={() => changeStatus(status)}
            >
              {ACTIONS[status].label}
            </button>
          ))}
        </div>
      )}
      {actionError && (
        <p className="admin-alert" role="alert">
          {actionError}
        </p>
      )}

      <div className="order-layout">
        <div className="order-main">
          <section className="admin-card">
            <h2>Items</h2>
            <ul className="order-lines">
              {lines.map((line, index) => (
                <li key={index}>
                  {line.image ? <img src={line.image} alt="" /> : <span />}
                  <div>
                    {line.slug ? (
                      <Link to={`/product/${line.slug}`} className="admin-link">
                        {line.name}
                      </Link>
                    ) : (
                      <span>{line.name} (removed from shop)</span>
                    )}
                    <small>
                      {line.quantity} × {formatPrice(line.price)}
                    </small>
                  </div>
                  <span>{formatPrice(line.subtotal)}</span>
                </li>
              ))}
            </ul>
            <dl className="order-totals">
              <div>
                <dt>Subtotal</dt>
                <dd>{formatPrice(order.subtotal)}</dd>
              </div>
              <div>
                <dt>Delivery</dt>
                <dd>{formatPrice(order.deliveryFee)}</dd>
              </div>
              <div className="order-totals-total">
                <dt>Total (cash on delivery)</dt>
                <dd>{formatPrice(order.total)}</dd>
              </div>
            </dl>
          </section>

          <section className="admin-card">
            <h2>Order notes</h2>
            {customer.notes ? (
              <p className="order-notes">{customer.notes}</p>
            ) : (
              <p className="order-muted">The customer didn't leave any notes.</p>
            )}
          </section>
        </div>

        <aside className="order-side">
          <section className="admin-card">
            <h2>Customer</h2>
            <p className="order-detail">
              <strong>{customer.fullName}</strong>
              <a href={`tel:${customer.phone}`} className="admin-link">
                {customer.phone}
              </a>
              {customer.email && (
                <a href={`mailto:${customer.email}`} className="admin-link">
                  {customer.email}
                </a>
              )}
            </p>
          </section>

          <section className="admin-card">
            <h2>Delivery address</h2>
            <p className="order-detail">
              <span>{customer.address}</span>
              <span>{customer.commune}</span>
              <span>{customer.wilaya}, Algeria</span>
            </p>
          </section>

          <section className="admin-card">
            <h2>History</h2>
            <ol className="order-history">
              {Object.keys(STATUSES)
                .filter((status) => history[status])
                .sort((a, b) => new Date(history[a]) - new Date(history[b]))
                .map((status) => (
                  <li key={status}>
                    <StatusBadge status={status} />
                    <small>{formatDate(history[status])}</small>
                  </li>
                ))}
            </ol>
          </section>
        </aside>
      </div>
    </section>
  )
}

export default AdminOrderPage

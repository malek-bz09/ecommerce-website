import { Link, useNavigate, useSearchParams } from 'react-router'
import { formatPrice } from '../../utils/formatPrice'
import { formatDate } from './formatDate'
import { STATUSES } from './orderStatus'
import StatusBadge from './StatusBadge'
import { useAdminData } from './useAdminData'
import './AdminPages.css'

function AdminOrdersPage() {
  const { data: orders, error, loading } = useAdminData('/admin/orders')
  const navigate = useNavigate()
  // The filter lives in the URL (?status=pending) so the dashboard can link to it
  const [searchParams] = useSearchParams()
  const filter = searchParams.get('status') ?? 'all'

  const countOf = (status) => orders?.filter((o) => o.status === status).length ?? 0
  const shown = filter === 'all' ? orders : orders?.filter((o) => o.status === filter)

  return (
    <section>
      <header className="admin-page-header">
        <h1>Orders</h1>
        {orders && <p>{countOf('pending')} waiting for confirmation</p>}
      </header>

      <nav className="admin-tabs" aria-label="Filter orders by status">
        <Link to="/admin/orders" className={filter === 'all' ? 'is-active' : undefined}>
          All<span>{orders?.length ?? ''}</span>
        </Link>
        {Object.entries(STATUSES).map(([status, { label }]) => (
          <Link
            key={status}
            to={`/admin/orders?status=${status}`}
            className={filter === status ? 'is-active' : undefined}
          >
            {label}
            <span>{orders ? countOf(status) : ''}</span>
          </Link>
        ))}
      </nav>

      {loading && <p className="admin-message">Loading orders…</p>}
      {error && <p className="admin-alert">{error}</p>}
      {shown?.length === 0 && <p className="admin-message">No orders here yet.</p>}

      {shown?.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Customer</th>
                <th>Delivery to</th>
                <th className="is-number">Items</th>
                <th className="is-number">Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((order) => (
                // The whole row opens the order; the link inside is for keyboard users
                <tr
                  key={order.id}
                  className="is-clickable"
                  onClick={() => navigate(`/admin/orders/${order.id}`)}
                >
                  <td>
                    <Link
                      to={`/admin/orders/${order.id}`}
                      className="admin-row-link"
                      onClick={(event) => event.stopPropagation()} // the row navigates already
                    >
                      {order.id}
                    </Link>
                    <small>{formatDate(order.createdAt)}</small>
                  </td>
                  <td>
                    {order.customer.fullName}
                    <small>{order.customer.phone}</small>
                  </td>
                  <td>
                    {order.customer.wilaya}
                    <small>{order.customer.commune}</small>
                  </td>
                  <td className="is-number">{order.itemCount}</td>
                  <td className="is-number">{formatPrice(order.total)}</td>
                  <td>
                    <StatusBadge status={order.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default AdminOrdersPage

import { Link, useNavigate, useSearchParams } from 'react-router'
import { formatPrice } from '../../utils/formatPrice'
import { formatDate } from './formatDate'
import { STATUSES } from './orderStatus'
import StatusBadge from './StatusBadge'
import { useAdminData } from './useAdminData'
import './AdminPages.css'

const PAGE_SIZE = 50

function AdminOrdersPage() {
  const navigate = useNavigate()
  // The filter and page live in the URL (?status=pending&page=2) so the dashboard can link to them
  const [searchParams] = useSearchParams()
  const filter = searchParams.get('status') ?? 'all'
  const page = Math.max(Number(searchParams.get('page')) || 1, 1)

  const query = new URLSearchParams({ page, size: PAGE_SIZE })
  if (filter !== 'all') query.set('status', filter)
  const { data, error, loading } = useAdminData(`/admin/orders?${query}`)

  // The server filters, and counts every status for the tabs
  const shown = data?.items
  const counts = data?.statusCounts
  const countOf = (status) => counts?.[status] ?? 0
  const allCount = counts ? Object.values(counts).reduce((sum, n) => sum + n, 0) : ''
  const pageLink = (n) => `/admin/orders?${new URLSearchParams({ ...(filter !== 'all' && { status: filter }), page: n })}`

  return (
    <section>
      <header className="admin-page-header">
        <h1>Orders</h1>
        {counts && <p>{countOf('pending')} waiting for confirmation</p>}
      </header>

      <nav className="admin-tabs" aria-label="Filter orders by status">
        <Link to="/admin/orders" className={filter === 'all' ? 'is-active' : undefined}>
          All<span>{allCount}</span>
        </Link>
        {Object.entries(STATUSES).map(([status, { label }]) => (
          <Link
            key={status}
            to={`/admin/orders?status=${status}`}
            className={filter === status ? 'is-active' : undefined}
          >
            {label}
            <span>{counts ? countOf(status) : ''}</span>
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
                      {order.orderNumber}
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

      {data?.pages > 1 && (
        <nav className="admin-pager" aria-label="Pages">
          {page > 1 && <Link to={pageLink(page - 1)}>← Newer</Link>}
          <span>
            Page {page} of {data.pages}
          </span>
          {page < data.pages && <Link to={pageLink(page + 1)}>Older →</Link>}
        </nav>
      )}
    </section>
  )
}

export default AdminOrdersPage

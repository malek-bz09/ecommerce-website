import { Link } from 'react-router'
import { useAuth } from '../../context/auth'
import { formatPrice } from '../../utils/formatPrice'
import { formatDate } from './formatDate'
import { STATUSES } from './orderStatus'
import StatusBadge from './StatusBadge'
import { useAdminData } from './useAdminData'
import './AdminPages.css'
import './AdminDashboardPage.css'

function AdminDashboardPage() {
  const { user } = useAuth()
  const { data: stats, error, loading } = useAdminData('/admin/stats')

  if (loading) return <p className="admin-message">Loading dashboard…</p>
  if (error) return <p className="admin-alert">{error}</p>

  const { statusCounts } = stats
  const totalOrders = Object.values(statusCounts).reduce((sum, n) => sum + n, 0)

  return (
    <section className="dashboard">
      <header className="admin-page-header">
        <h1>Welcome back, {user.fullName}</h1>
        <p>Here's how the shop is doing</p>
      </header>

      <div className="dashboard-tiles">
        <StatTile label="Revenue" value={formatPrice(stats.revenue)} note="From delivered orders" />
        <StatTile
          label="Awaiting payment"
          value={formatPrice(stats.awaitingPayment)}
          note="Confirmed, not delivered yet"
        />
        <StatTile
          label="To confirm"
          value={statusCounts.pending}
          note={statusCounts.pending === 1 ? 'Order waiting' : 'Orders waiting'}
          to="/admin/orders?status=pending"
        />
        <StatTile label="Customers" value={stats.customers} to="/admin/customers" />
        <StatTile
          label="Average order"
          value={formatPrice(stats.averageOrder)}
          note="Delivered orders"
        />
        <StatTile
          label="Return rate"
          value={stats.returnRate === null ? '—' : `${Math.round(stats.returnRate * 100)}%`}
          note="Of delivered or returned"
        />
      </div>

      <div className="dashboard-row">
        <section className="admin-card">
          <h2>Orders placed · last 14 days</h2>
          <OrdersChart days={stats.ordersPerDay} />
        </section>

        <section className="admin-card">
          <h2>Orders by status</h2>
          <ul className="dashboard-status">
            {Object.keys(STATUSES).map((status) => (
              <li key={status}>
                <Link to={`/admin/orders?status=${status}`}>
                  <StatusBadge status={status} />
                  <span className="dashboard-status-count">{statusCounts[status]}</span>
                </Link>
                {/* Share of all orders, as a thin gray bar */}
                <span className="dashboard-share">
                  <span
                    style={{
                      width: `${totalOrders ? (statusCounts[status] / totalOrders) * 100 : 0}%`,
                    }}
                  />
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="dashboard-row">
        <section className="admin-card">
          <h2>Recent orders</h2>
          {stats.recentOrders.length === 0 ? (
            <p className="dashboard-empty">No orders yet.</p>
          ) : (
            <ul className="dashboard-list">
              {stats.recentOrders.map((order) => (
                <li key={order.id} className="dashboard-order">
                  <span className="dashboard-list-main">
                    <Link to={`/admin/orders/${order.id}`} className="admin-link">
                      {order.orderNumber}
                    </Link>
                    <small>
                      {order.fullName} · {formatDate(order.createdAt)}
                    </small>
                  </span>
                  <span className="dashboard-list-value">{formatPrice(order.total)}</span>
                  <StatusBadge status={order.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="dashboard-stack">
          <section className="admin-card">
            <h2>Low stock</h2>
            {stats.lowStock.length === 0 ? (
              <p className="dashboard-empty">Everything is well stocked.</p>
            ) : (
              <ul className="dashboard-list">
                {stats.lowStock.map((product) => (
                  <li key={product.id}>
                    <img src={product.image} alt="" />
                    <Link to={`/admin/products/${product.id}`} className="dashboard-list-main admin-link">
                      {product.name}
                    </Link>
                    <span
                      className={`admin-status admin-status--${product.stock === 0 ? 'bad' : 'warn'}`}
                    >
                      {product.stock === 0 ? 'Sold out' : `${product.stock} left`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="admin-card">
            <h2>Best sellers</h2>
            {stats.topProducts.length === 0 ? (
              <p className="dashboard-empty">Confirm some sales to see your best sellers.</p>
            ) : (
              <ol className="dashboard-list">
                {stats.topProducts.map((product) => (
                  <li key={product.id}>
                    <img src={product.image} alt="" />
                    <span className="dashboard-list-main">{product.name}</span>
                    <span className="dashboard-list-value">{product.sold} sold</span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </section>
  )
}

function StatTile({ label, value, note, to }) {
  const content = (
    <>
      <span className="stat-label">{label}</span>
      {/* Prices use a non-breaking space ("DZD 115,700.00"); a normal one lets the
          amount wrap under "DZD" on narrow screens instead of being cut off */}
      <span className="stat-value">{String(value).replace('\u00a0', ' ')}</span>
      {note && <span className="stat-note">{note}</span>}
    </>
  )
  // Tiles with somewhere to go are links
  return to ? (
    <Link to={to} className="stat-tile is-link">
      {content}
    </Link>
  ) : (
    <div className="stat-tile">{content}</div>
  )
}

// "2026-10-15" → "15 Oct"
const formatDay = (isoDate) =>
  new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })

// Rounds the axis top up to a clean number: 3 → 4, 37 → 40, 0 → 2
function niceTop(max) {
  const half = Math.max(max / 2, 1)
  const power = 10 ** Math.floor(Math.log10(half))
  const step = [1, 2, 5, 10].map((n) => n * power).find((n) => n >= half)
  return step * 2
}

function OrdersChart({ days }) {
  const top = niceTop(Math.max(...days.map((d) => d.orders)))
  const ticks = [top, top / 2, 0]

  return (
    <div className="chart">
      <div className="chart-plot">
        {ticks.map((tick) => (
          <div key={tick} className="chart-grid" style={{ bottom: `${(tick / top) * 100}%` }}>
            <span>{tick}</span>
          </div>
        ))}

        <ol className="chart-columns">
          {days.map((day) => {
            const text = `${formatDay(day.date)}: ${day.orders} ${day.orders === 1 ? 'order' : 'orders'}`
            return (
              // Each column is focusable so keyboard users get the tooltip too
              <li key={day.date} className="chart-column" tabIndex={0} aria-label={text}>
                <span className="chart-bar" style={{ height: `${(day.orders / top) * 100}%` }} />
                <span className="chart-tooltip" role="tooltip">
                  {text}
                </span>
              </li>
            )
          })}
        </ol>
      </div>

      {/* Label every other day, counting back from today, so labels never collide */}
      <ol className="chart-labels" aria-hidden="true">
        {days.map((day, index) => (
          <li key={day.date}>{(days.length - 1 - index) % 2 === 0 ? formatDay(day.date) : ''}</li>
        ))}
      </ol>

      <details className="chart-table">
        <summary>Show as table</summary>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Day</th>
              <th className="is-number">Orders</th>
            </tr>
          </thead>
          <tbody>
            {days.map((day) => (
              <tr key={day.date}>
                <td>{formatDay(day.date)}</td>
                <td className="is-number">{day.orders}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

export default AdminDashboardPage

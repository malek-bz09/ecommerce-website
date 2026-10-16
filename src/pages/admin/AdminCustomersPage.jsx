import { formatPrice } from '../../utils/formatPrice'
import { formatDate } from './formatDate'
import { useAdminData } from './useAdminData'
import './AdminPages.css'

function AdminCustomersPage() {
  const { data: customers, error, loading } = useAdminData('/admin/customers')

  return (
    <section>
      <header className="admin-page-header">
        <h1>Customers</h1>
        {customers && <p>Buyers appear here once you confirm their sale</p>}
      </header>

      {loading && <p className="admin-message">Loading customers…</p>}
      {error && <p className="admin-alert">{error}</p>}
      {customers?.length === 0 && (
        <p className="admin-message">No customers yet. Confirm an order to add its buyer.</p>
      )}

      {customers?.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Contact</th>
                <th>Address</th>
                <th className="is-number">Orders</th>
                <th className="is-number">Total spent</th>
                <th>Last order</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id}>
                  <td>{customer.fullName}</td>
                  <td>
                    <a href={`tel:${customer.phone}`}>{customer.phone}</a>
                    <small>{customer.email}</small>
                  </td>
                  <td className="is-wrap">
                    {customer.address}
                    <small>
                      {customer.commune}, {customer.wilaya}
                    </small>
                  </td>
                  <td className="is-number">{customer.orderCount}</td>
                  <td className="is-number">{formatPrice(customer.totalSpent)}</td>
                  <td>{formatDate(customer.lastOrderAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default AdminCustomersPage

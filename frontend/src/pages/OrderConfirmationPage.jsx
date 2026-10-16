import { Link, Navigate, useLocation } from 'react-router'
import { formatPrice } from '../utils/formatPrice'
import './CartPage.css'
import './CheckoutPage.css'

function OrderConfirmationPage() {
  const order = useLocation().state?.order

  // Reached directly (refresh, typed URL) without a just-placed order
  if (!order) return <Navigate to="/" replace />

  const { id, customer, lines, subtotal, deliveryFee, total } = order

  return (
    <section className="cart-page confirmation">
      <p className="confirmation-eyebrow">Order {id}</p>
      <h1 className="cart-title">Thank you, {customer.fullName.split(' ')[0]}!</h1>
      <p className="confirmation-lead">
        Your order has been placed. We'll call you on <strong>{customer.phone}</strong> to confirm
        it before shipping. A summary was sent to {customer.email}.
      </p>

      <div className="confirmation-grid">
        <div>
          <h2>Delivery to</h2>
          <p>
            {customer.fullName}
            <br />
            {customer.address}
            <br />
            {customer.commune}, {customer.wilaya}
          </p>
          {customer.notes && <p className="confirmation-notes">“{customer.notes}”</p>}
        </div>

        <div className="cart-summary">
          <h2>Cash on delivery</h2>
          <ul className="checkout-lines">
            {lines.map((line) => (
              <li key={line.id}>
                <span>
                  {line.name} × {line.quantity}
                </span>
                <span>{formatPrice(line.price * line.quantity)}</span>
              </li>
            ))}
          </ul>
          <dl>
            <div>
              <dt>Subtotal</dt>
              <dd>{formatPrice(subtotal)}</dd>
            </div>
            <div>
              <dt>Delivery</dt>
              <dd>{formatPrice(deliveryFee)}</dd>
            </div>
            <div className="cart-summary-total">
              <dt>To pay on delivery</dt>
              <dd>{formatPrice(total)}</dd>
            </div>
          </dl>
        </div>
      </div>

      <Link to="/" className="cart-button confirmation-cta">
        Continue shopping
      </Link>
    </section>
  )
}

export default OrderConfirmationPage

import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useCart } from '../context/cart'
import { wilayas } from '../data/wilayas'
import { DELIVERY_FEE, OrderError, placeOrder } from '../services/orders'
import { formatPrice } from '../utils/formatPrice'
import { FIELDS, LIMITS, validateCheckout, validateField } from '../utils/validateCheckout'
import './CartPage.css'
import './CheckoutPage.css'

const EMPTY_FORM = Object.fromEntries(FIELDS.map((field) => [field, '']))

function CheckoutPage() {
  const { lines, subtotal, clearCart } = useCart()
  const navigate = useNavigate()

  const [values, setValues] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  // Items that can't be ordered as they are (sold out or over the stock limit)
  const stockIssues = lines.filter(({ quantity, product }) => quantity > product.stock)

  if (lines.length === 0) {
    return (
      <section className="cart-empty">
        <h1>Nothing to check out</h1>
        <p>Your cart is empty. Add some products before placing an order.</p>
        <Link to="/" className="cart-button">
          Continue shopping
        </Link>
      </section>
    )
  }

  const handleChange = (event) => {
    const { name, value } = event.target
    setValues((v) => ({ ...v, [name]: value }))
    // Only re-check while typing once the field has been visited, so we don't nag early
    if (touched[name]) setErrors((e) => ({ ...e, [name]: validateField(name, value) }))
  }

  const handleBlur = (event) => {
    const { name, value } = event.target
    setTouched((t) => ({ ...t, [name]: true }))
    setErrors((e) => ({ ...e, [name]: validateField(name, value) }))
  }

  const focusFirstError = (form, fieldErrors) => {
    const first = FIELDS.find((field) => fieldErrors[field])
    form.elements[first]?.focus()
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (submitting) return

    const form = event.currentTarget
    const fieldErrors = validateCheckout(values)
    setTouched(Object.fromEntries(FIELDS.map((field) => [field, true])))
    setErrors(fieldErrors)

    if (Object.keys(fieldErrors).length > 0) {
      setFormError('Please fix the highlighted fields below.')
      focusFirstError(form, fieldErrors)
      return
    }
    if (stockIssues.length > 0) {
      setFormError('Some items in your cart are no longer available in that quantity.')
      return
    }

    setSubmitting(true)
    setFormError(null)
    try {
      const order = await placeOrder({
        customer: values,
        items: lines.map(({ id, quantity }) => ({ id, quantity })),
      })
      navigate('/order-confirmed', { replace: true, state: { order } })
      clearCart()
    } catch (error) {
      if (error instanceof OrderError) {
        setFormError(error.cartChanged ? `${error.message} Review your cart.` : error.message)
        if (error.fieldErrors) {
          setErrors(error.fieldErrors)
          focusFirstError(form, error.fieldErrors)
        }
      } else {
        console.error(error)
        setFormError('Something went wrong while placing your order. Please try again.')
      }
      setSubmitting(false)
    }
  }

  // Shared props for every input: value, handlers and accessible error wiring
  const fieldProps = (name) => ({
    id: `checkout-${name}`,
    name,
    value: values[name],
    onChange: handleChange,
    onBlur: handleBlur,
    maxLength: LIMITS[name],
    disabled: submitting,
    'aria-invalid': Boolean(errors[name]),
    'aria-describedby': errors[name] ? `checkout-${name}-error` : undefined,
  })

  return (
    <section className="cart-page">
      <nav className="checkout-back">
        <Link to="/cart">← Back to cart</Link>
      </nav>
      <h1 className="cart-title">Checkout</h1>

      <div className="cart-layout">
        <form id="checkout-form" className="checkout-form" onSubmit={handleSubmit} noValidate>
          {formError && (
            <p className="checkout-alert" role="alert">
              {formError}
            </p>
          )}

          <fieldset>
            <legend>Contact</legend>
            <Field label="Full name" name="fullName" error={errors.fullName}>
              <input type="text" autoComplete="name" {...fieldProps('fullName')} />
            </Field>
            <div className="checkout-row">
              <Field label="Phone number" name="phone" error={errors.phone}>
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="0555 12 34 56"
                  {...fieldProps('phone')}
                />
              </Field>
              <Field label="Email" name="email" error={errors.email}>
                <input
                  type="email"
                  autoComplete="email"
                  placeholder="name@example.com"
                  {...fieldProps('email')}
                />
              </Field>
            </div>
          </fieldset>

          <fieldset>
            <legend>Delivery address</legend>
            <div className="checkout-row">
              <Field label="Wilaya" name="wilaya" error={errors.wilaya}>
                <select {...fieldProps('wilaya')}>
                  <option value="">Select a wilaya</option>
                  {wilayas.map(({ code, name }) => (
                    <option key={code} value={code}>
                      {code} – {name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Commune" name="commune" error={errors.commune}>
                <input type="text" autoComplete="address-level2" {...fieldProps('commune')} />
              </Field>
            </div>
            <Field label="Address" name="address" error={errors.address}>
              <input
                type="text"
                autoComplete="street-address"
                placeholder="Street, building, floor, apartment"
                {...fieldProps('address')}
              />
            </Field>
            <Field label="Order notes" name="notes" error={errors.notes} optional>
              <textarea
                rows={3}
                placeholder="Anything the delivery person should know"
                {...fieldProps('notes')}
              />
            </Field>
          </fieldset>

          <fieldset>
            <legend>Payment</legend>
            <label className="checkout-payment">
              <input type="radio" name="payment" value="cod" checked readOnly />
              <span>
                <strong>Cash on delivery</strong>
                Pay in cash when your order arrives. We'll call you to confirm before shipping.
              </span>
            </label>
          </fieldset>
        </form>

        <aside className="cart-summary">
          <h2>Order summary</h2>
          <ul className="checkout-lines">
            {lines.map(({ id, quantity, product }) => (
              <li key={id} className={quantity > product.stock ? 'has-issue' : undefined}>
                <span>
                  {product.name} × {quantity}
                  {quantity > product.stock && (
                    <small>
                      {product.stock === 0 ? 'Sold out' : `Only ${product.stock} left`}
                    </small>
                  )}
                </span>
                <span>{formatPrice(product.price * quantity)}</span>
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
              <dd>{formatPrice(DELIVERY_FEE)}</dd>
            </div>
            <div className="cart-summary-total">
              <dt>Total to pay on delivery</dt>
              <dd>{formatPrice(subtotal + DELIVERY_FEE)}</dd>
            </div>
          </dl>
          {stockIssues.length > 0 && (
            <p className="checkout-alert" role="alert">
              Update your <Link to="/cart">cart</Link> before ordering.
            </p>
          )}
          <button
            type="submit"
            form="checkout-form"
            className="cart-button"
            disabled={submitting || stockIssues.length > 0}
          >
            {submitting ? 'Placing order…' : 'Place order'}
          </button>
        </aside>
      </div>
    </section>
  )
}

function Field({ label, name, error, optional = false, children }) {
  return (
    <div className={`checkout-field${error ? ' has-error' : ''}`}>
      <label htmlFor={`checkout-${name}`}>
        {label}
        {optional && <span> (optional)</span>}
      </label>
      {children}
      {error && (
        <p id={`checkout-${name}-error`} className="checkout-error">
          {error}
        </p>
      )}
    </div>
  )
}

export default CheckoutPage

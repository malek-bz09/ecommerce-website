import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAuth } from '../../context/auth'
import { useProducts } from '../../context/products'
import { categories } from '../../data/products'
import { useAdminData } from './useAdminData'
import './AdminPages.css'
import './AdminProductFormPage.css'

const EMPTY = {
  name: '',
  description: '',
  category: '',
  price: '',
  compareAtPrice: '',
  stock: '',
  image: '',
}

// /admin/products/new → empty form; /admin/products/12 → load product 12, then the form
function AdminProductFormPage() {
  const { productId } = useParams()
  return productId ? <EditProduct productId={productId} /> : <ProductForm initial={EMPTY} />
}

function EditProduct({ productId }) {
  const { data: product, error, loading } = useAdminData(`/admin/products/${productId}`)

  if (loading) return <p className="admin-message">Loading product…</p>
  if (error) return <p className="admin-alert">{error}</p>

  // Inputs hold text, so numbers become strings (and "no old price" becomes "")
  const initial = {
    name: product.name,
    description: product.description,
    category: product.category,
    price: String(product.price),
    compareAtPrice: product.compareAtPrice === null ? '' : String(product.compareAtPrice),
    stock: String(product.stock),
    image: product.images[0],
  }
  return <ProductForm productId={productId} initial={initial} />
}

// "" → null (left empty), "1200" → 1200
const toNumber = (text) => (text.trim() === '' ? null : Number(text))

function ProductForm({ productId, initial }) {
  const { authFetch } = useAuth()
  const catalog = useProducts()
  const navigate = useNavigate()
  const [values, setValues] = useState(initial)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)

  const isNew = !productId

  const handleChange = (event) => {
    const { name, value } = event.target
    setValues((v) => ({ ...v, [name]: value }))
    setErrors((e) => ({ ...e, [name]: null })) // clear a field's error once it's edited
  }

  const handleImage = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    const body = new FormData()
    body.append('file', file)
    setUploading(true)
    setErrors((e) => ({ ...e, image: null }))
    try {
      const { url } = await authFetch('/admin/uploads', { method: 'POST', body })
      setValues((v) => ({ ...v, image: url }))
    } catch (err) {
      setErrors((e) => ({ ...e, image: err.message }))
    } finally {
      setUploading(false)
      event.target.value = '' // lets you pick the same file again
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await authFetch(isNew ? '/admin/products' : `/admin/products/${productId}`, {
        method: isNew ? 'POST' : 'PUT',
        body: {
          ...values,
          price: toNumber(values.price),
          compareAtPrice: toNumber(values.compareAtPrice),
          stock: toNumber(values.stock),
        },
      })
      catalog.reload() // so the shop shows the change straight away
      navigate('/admin/products')
    } catch (err) {
      setFormError(err.message)
      setErrors(err.data?.fieldErrors ?? {})
      setSaving(false)
    }
  }

  // Shared props for each input
  const field = (name) => ({
    id: `product-${name}`,
    name,
    value: values[name],
    onChange: handleChange,
    disabled: saving,
    'aria-invalid': Boolean(errors[name]),
  })

  return (
    <section>
      <Link to="/admin/products" className="admin-back">
        ← All products
      </Link>
      <header className="admin-page-header">
        <h1>{isNew ? 'New product' : 'Edit product'}</h1>
      </header>

      {formError && (
        <p className="admin-alert" role="alert">
          {formError}
        </p>
      )}

      <form className="product-form" onSubmit={handleSubmit}>
        <div className="admin-card product-form-fields">
          <Field label="Name" name="name" error={errors.name}>
            <input type="text" maxLength={120} required {...field('name')} />
          </Field>

          <Field label="Description" name="description" error={errors.description}>
            <textarea rows={4} maxLength={1000} {...field('description')} />
          </Field>

          <Field label="Category" name="category" error={errors.category}>
            <select required {...field('category')}>
              <option value="">Choose a category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>

          <div className="product-form-row">
            <Field label="Price (DZD)" name="price" error={errors.price}>
              <input type="number" min={1} step={1} required {...field('price')} />
            </Field>
            <Field
              label="Old price (DZD)"
              name="compareAtPrice"
              error={errors.compareAtPrice}
              hint="Optional. Shows the product as on sale."
            >
              <input type="number" min={1} step={1} {...field('compareAtPrice')} />
            </Field>
            <Field label="Quantity in stock" name="stock" error={errors.stock}>
              <input type="number" min={0} step={1} required {...field('stock')} />
            </Field>
          </div>
        </div>

        <div className="admin-card product-form-image">
          <h2>Photo</h2>
          {values.image ? (
            <img src={values.image} alt="Product preview" />
          ) : (
            <div className="product-form-image-empty">No photo yet</div>
          )}
          <label className="admin-button admin-button--secondary product-form-upload">
            {uploading ? 'Uploading…' : values.image ? 'Change photo' : 'Upload photo'}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleImage}
              disabled={uploading || saving}
            />
          </label>
          <p className="product-form-hint">JPG, PNG or WebP, up to 5 MB. Portrait (4:5) looks best.</p>
          {errors.image && <p className="product-form-error">{errors.image}</p>}
        </div>

        <div className="product-form-actions">
          <button type="submit" className="admin-button" disabled={saving || uploading}>
            {saving ? 'Saving…' : isNew ? 'Create product' : 'Save changes'}
          </button>
          <Link to="/admin/products" className="admin-link">
            Cancel
          </Link>
        </div>
      </form>
    </section>
  )
}

function Field({ label, name, error, hint, children }) {
  return (
    <div className="product-form-field">
      <label htmlFor={`product-${name}`}>{label}</label>
      {children}
      {hint && !error && <p className="product-form-hint">{hint}</p>}
      {error && <p className="product-form-error">{error}</p>}
    </div>
  )
}

export default AdminProductFormPage

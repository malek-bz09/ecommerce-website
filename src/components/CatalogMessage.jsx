import './CatalogMessage.css'

// Shown while products load, or when they couldn't be loaded
function CatalogMessage({ error }) {
  return (
    <p className="catalog-message" role={error ? 'alert' : 'status'}>
      {error ?? 'Loading products…'}
    </p>
  )
}

export default CatalogMessage

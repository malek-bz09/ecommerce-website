import { Link, useSearchParams } from 'react-router'
import CatalogMessage from '../components/CatalogMessage'
import ProductGrid from '../components/ProductGrid'
import { useProducts } from '../context/products'
import { getCategoryName } from '../data/products'
import './SearchPage.css'

// "Café" → "cafe" and "Levi's" → "levis", so people find things however they type them
const normalize = (text) =>
  text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/['’]/g, '')
    .toLowerCase()

function SearchPage() {
  const [searchParams] = useSearchParams()
  const query = (searchParams.get('q') ?? '').trim()
  const { products, loading, error } = useProducts()

  if (loading || error) return <CatalogMessage error={error} />

  // Every word typed must appear in the name, description or category
  const words = normalize(query).split(/\s+/).filter(Boolean)
  const results = products.filter((product) => {
    const text = normalize(
      `${product.name} ${product.description} ${getCategoryName(product.category)}`,
    )
    return words.length > 0 && words.every((word) => text.includes(word))
  })

  if (results.length === 0) {
    return (
      <section className="search-empty">
        <h1>{query ? `No results for “${query}”` : 'Search the shop'}</h1>
        <p>
          {query
            ? 'Check the spelling or try a more general word, like “jeans” or “hat”.'
            : 'Type what you’re looking for in the search bar above.'}
        </p>
        <Link to="/" className="search-empty-link">
          See all products
        </Link>
      </section>
    )
  }

  const label = `${results.length} ${results.length === 1 ? 'result' : 'results'} for “${query}”`
  return <ProductGrid title={label} products={results} />
}

export default SearchPage

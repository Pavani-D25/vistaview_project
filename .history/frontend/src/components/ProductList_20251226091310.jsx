import { useState, useEffect } from 'react'
import axios from 'axios'
import './ProductList.css'

function ProductList({ refreshTrigger }) {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const limit = 20

  const fetchProducts = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const params = {
        skip: page * limit,
        limit: limit,
      }
      
      if (searchQuery) {
        params.q = searchQuery
      }

      const response = await axios.get('/api/products', { params })
      setProducts(response.data.products)
      setTotal(response.data.total)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts()
  }, [page, searchQuery, refreshTrigger])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(0)
  }

  const totalPages = Math.ceil(total / limit)

  if (loading && products.length === 0) {
    return (
      <div className="product-list">
        <h2>📦 Product Catalog</h2>
        <div className="loading">Loading products...</div>
      </div>
    )
  }

  return (
    <div className="product-list">
      <div className="list-header">
        <h2>📦 Product Catalog</h2>
        <div className="product-count">
          {total} {total === 1 ? 'product' : 'products'}
        </div>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          placeholder="Search by SKU, name, or category..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        <button type="submit" className="search-button">
          🔍 Search
        </button>
        {searchQuery && (
          <button
            type="button"
            onClick={() => {
              setSearchQuery('')
              setPage(0)
            }}
            className="clear-button"
          >
            Clear
          </button>
        )}
      </form>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {products.length === 0 && !loading ? (
        <div className="empty-state">
          <p>No products found. Upload a PDF catalog to get started!</p>
        </div>
      ) : (
        <>
          <div className="products-grid">
            {products.map((product) => (
              <div key={product.id} className="product-card">
                {product.collage_url ? (
                  <div className="product-image-container">
                    <img
                      src={product.collage_url}
                      alt={product.cn_name || product.sku_code}
                      className="product-image"
                      loading="lazy"
                    />
                  </div>
                ) : product.image_url ? (
                  <div className="product-image-container">
                    <img
                      src={product.image_url}
                      alt={product.cn_name || product.sku_code}
                      className="product-image"
                      loading="lazy"
                    />
                  </div>
                ) : (
                  <div className="product-image-placeholder">
                    <span>📷</span>
                    <p>No image</p>
                  </div>
                )}

                <div className="product-info">
                  {product.sku_code && (
                    <div className="product-sku">{product.sku_code}</div>
                  )}
                  
                  {product.cn_name && (
                    <h3 className="product-name">{product.cn_name}</h3>
                  )}
                  
                  {product.category && (
                    <div className="product-category">
                      🏷️ {product.category}
                    </div>
                  )}
                  
                  {(product.dims_l || product.dims_w || product.dims_h) && (
                    <div className="product-dimensions">
                      📏 {product.dims_l || '?'} × {product.dims_w || '?'} × {product.dims_h || '?'} mm
                    </div>
                  )}
                  
                  {product.description && (
                    <p className="product-description">{product.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 0}
                className="page-button"
              >
                ← Previous
              </button>
              
              <span className="page-info">
                Page {page + 1} of {totalPages}
              </span>
              
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages - 1}
                className="page-button"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ProductList

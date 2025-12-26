import React, { useState, useEffect } from 'react'
import UploadForm from './components/UploadForm'
import ProductList from './components/ProductList'
import './App.css'

function App() {
  const [uploadResult, setUploadResult] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleUploadSuccess = (result) => {
    setUploadResult(result)
    // Trigger product list refresh
    setRefreshTrigger(prev => prev + 1)
    
    // Clear the success message after 5 seconds
    setTimeout(() => {
      setUploadResult(null)
    }, 5000)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏠 VistaView Catalog</h1>
        <p>Upload vendor PDF catalogs and manage product inventory</p>
      </header>

      <main className="app-main">
        <section className="upload-section">
          <UploadForm onSuccess={handleUploadSuccess} />
          
          {uploadResult && (
            <div className="success-message">
              <h3>✅ Upload Successful!</h3>
              <div className="result-stats">
                <div className="stat">
                  <span className="stat-label">Pages Processed:</span>
                  <span className="stat-value">{uploadResult.message}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Products Created:</span>
                  <span className="stat-value">{uploadResult.products_created}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Images Extracted:</span>
                  <span className="stat-value">{uploadResult.images_extracted}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Collages Created:</span>
                  <span className="stat-value">{uploadResult.collages_created}</span>
                </div>
                {uploadResult.session_id && uploadResult.session_id !== 'N/A' && (
                  <div className="stat">
                    <span className="stat-label">Session ID:</span>
                    <span className="stat-value">{uploadResult.session_id}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="products-section">
          <ProductList refreshTrigger={refreshTrigger} />
        </section>
      </main>
    </div>
  )
}

export default App

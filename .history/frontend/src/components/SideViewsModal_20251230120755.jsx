import React, { useState } from 'react';
import './SideViewsModal.css';

const SideViewsModal = ({ product, onClose }) => {
  const [views, setViews] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Generate views when modal opens
  React.useEffect(() => {
    generateViews();
  }, []);

  const generateViews = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/products/${product.id}/generate-views`,
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate views');
      }

      const data = await response.json();
      setViews(data.views);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Side Views - {product.name}</h2>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Generating side views...</p>
              <p className="loading-note">This may take 30-60 seconds</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p className="error-message">{error}</p>
              <button className="retry-button" onClick={generateViews}>
                Retry
              </button>
            </div>
          )}

          {views && !loading && (
            <div className="views-grid">
              {Object.entries(views).map(([viewName, url]) => {
                // Parse view name (e.g., "left_15" -> "Left 15°")
                const [direction, angle] = viewName.split('_');
                const label = `${direction.charAt(0).toUpperCase() + direction.slice(1)} ${angle}°`;

                return (
                  <div key={viewName} className="view-item">
                    <img src={url} alt={label} />
                    <p className="view-label">{label}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SideViewsModal;

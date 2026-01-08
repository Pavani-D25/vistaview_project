import React, { useState, useEffect } from 'react';
import './SideViewsModal.css';

const DESIRED_ANGLES = [15, 30, 45];

const SideViewsModal = ({ product, onClose }) => {
  const [views, setViews] = useState(product.side_views_urls || {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentAngleIndex, setCurrentAngleIndex] = useState(0);

  // Start generating views angle-by-angle when modal opens
  useEffect(() => {
    generateNextAngle(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const generateNextAngle = async (angleIndex) => {
    if (angleIndex >= DESIRED_ANGLES.length) {
      setLoading(false);
      return;
    }

    const angle = DESIRED_ANGLES[angleIndex];
    setLoading(true);
    setError(null);
    setCurrentAngleIndex(angleIndex);

    try {
      const response = await fetch(
        `/api/products/${product.id}/generate-views?angles=${angle}`,
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate views');
      }

      const data = await response.json();

      // Merge newly generated views into existing ones so they appear incrementally
      setViews((prev) => ({
        ...prev,
        ...(data.views || {}),
      }));

      // Proceed to the next angle
      await generateNextAngle(angleIndex + 1);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Side Views - {product.cn_name || product.sku_code}</h2>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Generating side views...</p>
              <p className="loading-note">
                Working on angle {DESIRED_ANGLES[currentAngleIndex]}° of {DESIRED_ANGLES[DESIRED_ANGLES.length - 1]}°
              </p>
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

          {views && Object.keys(views).length > 0 && (
            <div className="views-grid">
              {Object.entries(views).map(([viewName, url]) => {
                // viewName can be like "left_15", "right_30", etc.
                const [direction, angle] = viewName.split('_');
                const prettyDirection = direction.charAt(0).toUpperCase() + direction.slice(1);
                const label = `${prettyDirection} ${angle ? angle + '°' : ''}`.trim();

                const emojis = {
                  top: '⬆️',
                  bottom: '⬇️',
                  left: '⬅️',
                  right: '➡️',
                };
                const emoji = emojis[direction] || '🔄';

                return (
                  <div key={viewName} className="view-item">
                    <img src={url} alt={label} />
                    <p className="view-label">{emoji} {label}</p>
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

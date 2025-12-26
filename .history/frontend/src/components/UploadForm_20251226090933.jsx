import React, { useState } from 'react'
import axios from 'axios'
import './UploadForm.css'

function UploadForm({ onSuccess }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setError(null)
    } else {
      setError('Please select a valid PDF file')
      setFile(null)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile)
        setError(null)
      } else {
        setError('Please drop a valid PDF file')
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a PDF file')
      return
    }

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      if (response.data.status === 'success') {
        onSuccess(response.data)
        setFile(null)
        // Reset file input
        document.getElementById('file-input').value = ''
      } else {
        setError(response.data.message || 'Upload failed')
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-form">
      <h2>📄 Upload PDF Catalog</h2>
      
      <form onSubmit={handleSubmit}>
        <div 
          className={`file-drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={uploading}
            style={{ display: 'none' }}
          />
          
          {!file ? (
            <label htmlFor="file-input" className="file-label">
              <div className="upload-icon">📁</div>
              <p className="upload-text">
                <strong>Click to upload</strong> or drag and drop
              </p>
              <p className="upload-hint">PDF files only</p>
            </label>
          ) : (
            <div className="file-selected">
              <div className="file-icon">📄</div>
              <div className="file-info">
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setFile(null)
                  document.getElementById('file-input').value = ''
                }}
                className="remove-file"
                disabled={uploading}
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="upload-button"
        >
          {uploading ? (
            <>
              <span className="spinner"></span>
              Processing...
            </>
          ) : (
            <>
              ⬆️ Upload & Process
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default UploadForm

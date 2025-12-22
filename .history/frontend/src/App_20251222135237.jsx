import { Routes, Route, Navigate } from 'react-router-dom'
import DisplayImages from './pages/DisplayImages'
import Input from './pages/Input'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Input />} />
      <Route path="/images" element={<DisplayImages />} />
      {/* Backward-compat for old link */}
      <Route path="/DisplayImages" element={<Navigate to="/images" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App

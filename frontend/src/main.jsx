import './i18n'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import App from './App'
import './index.css'

const basename = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || ''
ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <React.StrictMode>
      <BrowserRouter basename={basename || undefined}>
        <App />
      </BrowserRouter>
    </React.StrictMode>
  </ErrorBoundary>
)

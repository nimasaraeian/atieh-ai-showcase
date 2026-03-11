import React from 'react'

export class ErrorBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('App error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 p-6 text-slate-200">
          <h1 className="mb-4 text-lg font-semibold text-red-400">خطا در بارگذاری صفحه</h1>
          <pre className="max-w-2xl overflow-auto rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-300">
            {this.state.error?.toString?.() || String(this.state.error)}
          </pre>
          <button
            onClick={() => {
              this.setState({ error: null })
              window.location.reload()
            }}
            className="mt-6 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
          >
            بارگذاری مجدد
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

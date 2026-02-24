import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import AppLayout from './components/layout/AppLayout'
import Dashboard from './pages/Dashboard'
import Notas from './pages/Notas'
import Estatisticas from './pages/Estatisticas'
import Planos from './pages/Planos'
import Configuracoes from './pages/Configuracoes'
import Perfil from './pages/Perfil'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0f1923',
            color: '#e2e8f0',
            border: '1px solid #1e2d42',
            borderRadius: '10px',
          },
          success: { iconTheme: { primary: '#22a56c', secondary: '#0f1923' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0f1923' } },
        }}
      />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/cadastro" element={<PublicRoute><Register /></PublicRoute>} />
        
        <Route path="/" element={<PrivateRoute><AppLayout /></PrivateRoute>}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="notas" element={<Notas />} />
          <Route path="estatisticas" element={<Estatisticas />} />
          <Route path="planos" element={<Planos />} />
          <Route path="configuracoes" element={<Configuracoes />} />
          <Route path="perfil" element={<Perfil />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

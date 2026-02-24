import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

interface User {
  id: string
  nome: string
  email: string
  role: string
}

interface Empresa {
  id: string
  nome: string
  cnpj: string
  status: string
  trial_expira_em: string | null
  certificado_configurado: boolean
  plano_id: string | null
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  empresa: Empresa | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: any) => Promise<void>
  logout: () => void
  fetchEmpresa: () => Promise<void>
  setTokens: (access: string, refresh: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      empresa: null,
      isAuthenticated: false,

      setTokens: (access, refresh) => {
        set({ accessToken: access, refreshToken: refresh })
      },

      login: async (email, password) => {
        const res = await api.post('/auth/login', { email, senha: password })
        const { access_token, refresh_token, usuario } = res.data
        set({
          accessToken: access_token,
          refreshToken: refresh_token,
          user: usuario,
          isAuthenticated: true,
        })
        // Carrega empresa após login
        try {
          const empRes = await api.get('/empresa/me')
          set({ empresa: empRes.data })
        } catch {}
      },

      register: async (data) => {
        const res = await api.post('/auth/register', data)
        const { access_token, refresh_token, usuario } = res.data
        set({
          accessToken: access_token,
          refreshToken: refresh_token,
          user: usuario,
          isAuthenticated: true,
        })
        try {
          const empRes = await api.get('/empresa/me')
          set({ empresa: empRes.data })
        } catch {}
      },

      fetchEmpresa: async () => {
        try {
          const res = await api.get('/empresa/me')
          set({ empresa: res.data })
        } catch {}
      },

      logout: () => {
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          empresa: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'fiscalspy-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        empresa: state.empresa,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

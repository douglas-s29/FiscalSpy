import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, FileText, BarChart3, CreditCard,
  Settings, User, LogOut, Radar, ChevronLeft, Bell
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/notas', icon: FileText, label: 'Notas Fiscais' },
  { to: '/estatisticas', icon: BarChart3, label: 'Estatísticas' },
  { to: '/planos', icon: CreditCard, label: 'Planos' },
]

const bottomItems = [
  { to: '/configuracoes', icon: Settings, label: 'Configurações' },
  { to: '/perfil', icon: User, label: 'Perfil' },
]

const statusColors: Record<string, string> = {
  trial: 'bg-yellow-500',
  ativo: 'bg-brand-500',
  bloqueado: 'bg-red-500',
  inadimplente: 'bg-red-500',
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const { logout, empresa, user } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const statusDot = empresa?.status ? statusColors[empresa.status] : 'bg-slate-500'

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* Sidebar */}
      <aside className={`flex flex-col border-r border-dark-500 bg-dark-800 transition-all duration-200 flex-shrink-0 ${collapsed ? 'w-[60px]' : 'w-[220px]'}`}>
        {/* Logo */}
        <div className={`flex items-center h-14 border-b border-dark-500 px-3 gap-2.5 ${collapsed ? 'justify-center' : ''}`}>
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center flex-shrink-0">
            <Radar size={14} className="text-white" />
          </div>
          {!collapsed && (
            <span className="font-bold text-white text-sm">FiscalSpy</span>
          )}
        </div>

        {/* Empresa badge */}
        {!collapsed && empresa && (
          <div className="mx-3 my-2 px-3 py-2 rounded-lg bg-dark-700 border border-dark-500">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot}`}></span>
              <span className="text-xs text-slate-300 truncate">{empresa.nome || 'Empresa'}</span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 truncate font-mono">{empresa.cnpj || ''}</p>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 flex flex-col gap-0.5 p-2 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-500/15 text-brand-400 font-medium'
                    : 'text-slate-400 hover:text-white hover:bg-dark-600'
                } ${collapsed ? 'justify-center' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={17} className="flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Bottom nav */}
        <div className="flex flex-col gap-0.5 p-2 border-t border-dark-500">
          {bottomItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-brand-500/15 text-brand-400' : 'text-slate-400 hover:text-white hover:bg-dark-600'
                } ${collapsed ? 'justify-center' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={17} className="flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
          <button
            onClick={handleLogout}
            className={`flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors ${collapsed ? 'justify-center' : ''}`}
            title={collapsed ? 'Sair' : undefined}
          >
            <LogOut size={17} className="flex-shrink-0" />
            {!collapsed && <span>Sair</span>}
          </button>

          {/* Collapse button */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs text-slate-500 hover:text-slate-300 hover:bg-dark-600 transition-colors mt-1 ${collapsed ? 'justify-center' : ''}`}
          >
            <ChevronLeft size={15} className={`flex-shrink-0 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
            {!collapsed && <span>Recolher</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-14 border-b border-dark-500 bg-dark-800 flex items-center px-5 gap-3 flex-shrink-0">
          <input
            type="text"
            placeholder="Buscar notas, chaves..."
            className="flex-1 max-w-xs bg-dark-700 border border-dark-500 rounded-lg px-3 py-1.5 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-brand-500/50"
          />
          <div className="ml-auto flex items-center gap-2">
            {/* Notifications */}
            <button className="w-8 h-8 rounded-lg hover:bg-dark-600 flex items-center justify-center text-slate-400 hover:text-white transition-colors relative">
              <Bell size={17} />
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-8 h-8 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400 hover:bg-brand-500/30 transition-colors text-xs font-bold"
              >
                {(empresa?.nome || user?.nome || 'U')[0].toUpperCase()}
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-10 w-48 bg-dark-700 border border-dark-500 rounded-xl shadow-xl z-50 py-1.5">
                  <div className="px-3 py-2 border-b border-dark-500 mb-1">
                    <p className="text-white text-sm font-medium truncate">{empresa?.nome || user?.nome}</p>
                    <p className="text-slate-400 text-xs truncate">{user?.email}</p>
                  </div>
                  <NavLink
                    to="/perfil"
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-300 hover:text-white hover:bg-dark-600 transition-colors"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <User size={14} /> Perfil
                  </NavLink>
                  <NavLink
                    to="/configuracoes"
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-300 hover:text-white hover:bg-dark-600 transition-colors"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings size={14} /> Configurações
                  </NavLink>
                  <div className="border-t border-dark-500 mt-1 pt-1">
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <LogOut size={14} /> Sair
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

import { useEffect } from 'react'
import { User, Building2, CreditCard, ShieldCheck } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const statusLabel: Record<string, { label: string; color: string }> = {
  trial: { label: 'Trial ativo', color: 'text-yellow-400' },
  ativo: { label: 'Ativo', color: 'text-brand-400' },
  bloqueado: { label: 'Bloqueado', color: 'text-red-400' },
  inadimplente: { label: 'Inadimplente', color: 'text-red-400' },
}

export default function Perfil() {
  const { empresa, user, fetchEmpresa } = useAuthStore()

  useEffect(() => {
    fetchEmpresa()
  }, [])

  const status = empresa?.status ? statusLabel[empresa.status] : null

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-6">Perfil</h1>

      {/* Avatar */}
      <div className="card flex items-center gap-4 mb-4">
        <div className="w-14 h-14 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
          <User size={24} className="text-brand-400" />
        </div>
        <div>
          <p className="text-white font-semibold text-lg">{empresa?.nome || user?.nome || '—'}</p>
          <p className="text-slate-400 text-sm">{user?.email || '—'}</p>
        </div>
      </div>

      {/* Informações */}
      <div className="card">
        <h2 className="text-white font-semibold mb-4">Informações da Conta</h2>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between py-2 border-b border-dark-500">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Building2 size={15} /> CNPJ
            </div>
            <span className="text-white text-sm font-mono">{empresa?.cnpj || '—'}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dark-500">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Building2 size={15} /> Empresa
            </div>
            <span className="text-white text-sm">{empresa?.nome || '—'}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-dark-500">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <ShieldCheck size={15} /> Status
            </div>
            <span className={`text-sm font-medium ${status?.color || 'text-slate-400'}`}>
              {status?.label || '—'}
            </span>
          </div>
          {empresa?.trial_expira_em && (
            <div className="flex items-center justify-between py-2 border-b border-dark-500">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <ShieldCheck size={15} /> Trial expira
              </div>
              <span className="text-white text-sm">
                {new Date(empresa.trial_expira_em).toLocaleDateString('pt-BR')}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <CreditCard size={15} /> Plano
            </div>
            <span className="text-white text-sm">
              {empresa?.plano_id ? 'Plano ativo' : 'Trial / Sem plano'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

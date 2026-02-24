import { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Check, CreditCard, Zap, Crown, Star } from 'lucide-react'
import clsx from 'clsx'

interface Plano {
  id: string
  nome: string
  limite_notas: number
  limite_empresas: number
  valor_mensal: number
  ativo: boolean
}

const planIcons: Record<string, any> = {
  Starter: Zap,
  Business: Star,
  Enterprise: Crown,
}

export default function Planos() {
  const [planos, setPlanos] = useState<Plano[]>([])
  const [loading, setLoading] = useState(true)
  const [assinaturaStatus, setAssinaturaStatus] = useState<any>(null)
  const { empresa } = useAuthStore()

  useEffect(() => {
    Promise.all([
      api.get('/planos'),
      api.get('/assinatura/status')
    ]).then(([p, a]) => {
      setPlanos(p.data)
      setAssinaturaStatus(a.data)
    }).catch(() => toast.error('Erro ao carregar planos')).finally(() => setLoading(false))
  }, [])

  const handleAssinar = async (plano_id: string) => {
    try {
      await api.post('/assinatura/criar', { plano_id, ciclo: 'MONTHLY' })
      toast.success('Assinatura criada! Aguarde o processamento do pagamento.')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Erro ao criar assinatura')
    }
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h1 className="page-title">Planos & Assinatura</h1>
        <p className="text-slate-400 text-sm mt-0.5">Gerencie sua assinatura do FiscalSpy</p>
      </div>

      {/* Current subscription status */}
      {assinaturaStatus && (
        <div className="card border-brand-500/20 bg-brand-500/5">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <CreditCard size={18} className="text-brand-400" />
            </div>
            <div>
              <p className="font-semibold text-white">Status da Assinatura</p>
              <div className="flex items-center gap-3 mt-0.5">
                <span className={clsx('text-sm font-medium', {
                  'text-brand-400': assinaturaStatus.empresa_status === 'ativo',
                  'text-yellow-400': assinaturaStatus.empresa_status === 'trial',
                  'text-red-400': assinaturaStatus.empresa_status === 'bloqueado' || assinaturaStatus.empresa_status === 'inadimplente',
                })}>
                  {assinaturaStatus.empresa_status === 'trial' ? '🎁 Trial ativo' :
                   assinaturaStatus.empresa_status === 'ativo' ? '✅ Ativo' :
                   assinaturaStatus.empresa_status === 'inadimplente' ? '⚠️ Pagamento pendente' :
                   '🔒 Bloqueado'}
                </span>
                {assinaturaStatus.trial_expira_em && assinaturaStatus.empresa_status === 'trial' && (
                  <span className="text-slate-400 text-sm">
                    Expira em: {new Date(assinaturaStatus.trial_expira_em).toLocaleDateString('pt-BR')}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plans */}
      {loading ? (
        <div className="grid md:grid-cols-3 gap-5">
          {[...Array(3)].map((_, i) => <div key={i} className="card h-96 skeleton rounded-xl" />)}
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-5">
          {planos.map((plano, idx) => {
            const Icon = planIcons[plano.nome] || Zap
            const highlighted = idx === 1
            const isCurrentPlan = empresa?.plano_id === plano.id

            return (
              <div
                key={plano.id}
                className={clsx(
                  'relative rounded-xl border p-6 flex flex-col transition-all',
                  highlighted
                    ? 'bg-brand-500/5 border-brand-500/30 shadow-xl shadow-brand-500/10'
                    : 'card',
                  isCurrentPlan && 'ring-2 ring-brand-500'
                )}
              >
                {highlighted && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-brand-500 text-white text-xs font-bold rounded-full">
                    MAIS POPULAR
                  </div>
                )}
                {isCurrentPlan && (
                  <div className="absolute -top-3.5 right-4 px-3 py-1 bg-dark-600 border border-brand-500/40 text-brand-400 text-xs font-bold rounded-full">
                    SEU PLANO
                  </div>
                )}

                <div className="flex items-center gap-3 mb-4">
                  <div className={clsx(
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    highlighted ? 'bg-brand-500/20 border border-brand-500/30' : 'bg-dark-600 border border-dark-400'
                  )}>
                    <Icon size={18} className={highlighted ? 'text-brand-400' : 'text-slate-400'} />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">{plano.nome}</h3>
                  </div>
                </div>

                <div className="mb-5">
                  <span className="text-4xl font-bold text-white">
                    R$ {Number(plano.valor_mensal).toLocaleString('pt-BR')}
                  </span>
                  <span className="text-slate-400 text-sm">/mês</span>
                </div>

                <ul className="flex-1 flex flex-col gap-2.5 mb-6">
                  {[
                    `${plano.limite_empresas === -1 ? 'Ilimitados' : plano.limite_empresas} CNPJ(s) monitorado(s)`,
                    `${plano.limite_notas === -1 ? 'Ilimitadas' : plano.limite_notas.toLocaleString('pt-BR')} notas/mês`,
                    'Download de XML',
                    'Export Excel e ZIP',
                    highlighted ? 'Manifestação automática' : null,
                    highlighted ? 'Suporte prioritário' : null,
                    idx === 2 ? 'Gerente de conta dedicado' : null,
                    idx === 2 ? 'SLA 99.9%' : null,
                  ].filter(Boolean).map((feature) => (
                    <li key={feature as string} className="flex items-center gap-2.5 text-sm text-slate-300">
                      <Check size={14} className="text-brand-400 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => !isCurrentPlan && handleAssinar(plano.id)}
                  disabled={isCurrentPlan}
                  className={clsx(
                    'w-full text-center py-2.5 rounded-lg font-semibold text-sm transition-all',
                    isCurrentPlan
                      ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20 cursor-default'
                      : highlighted
                      ? 'btn-primary'
                      : 'btn-secondary'
                  )}
                >
                  {isCurrentPlan ? 'Plano Atual' : 'Assinar Agora'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-center text-sm text-slate-500">
        Pagamentos processados com segurança via Asaas · Cancele a qualquer momento
      </p>
    </div>
  )
}

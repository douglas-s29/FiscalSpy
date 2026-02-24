import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import api from '../services/api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { FileText, TrendingUp, TrendingDown, AlertCircle, RefreshCw, Clock, CheckCircle, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

interface Stats {
  total_entrada_mes: number
  total_saida_mes: number
  total_canceladas: number
  valor_total_mensal: number
  grafico_mensal: { mes: string; total: number }[]
}

interface SefazStatus {
  ultimo_nsu: number
  ultima_sincronizacao: string | null
  status_worker: string
  certificado_configurado: boolean
}

const formatCurrency = (v: number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v)

export default function Dashboard() {
  const { empresa } = useAuthStore()
  const [stats, setStats] = useState<Stats | null>(null)
  const [sefazStatus, setSefazStatus] = useState<SefazStatus | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAll()
  }, [])

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [s, ss] = await Promise.all([
        api.get('/notas/estatisticas'),
        api.get('/sefaz/status')
      ])
      setStats(s.data)
      setSefazStatus(ss.data)
    } catch (err: any) {
      if (err.response?.status !== 402 && err.response?.status !== 403) {
        toast.error('Erro ao carregar dados')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const { data } = await api.post('/sefaz/sincronizar')
      toast.success(data.mensagem)
      fetchAll()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Erro ao sincronizar')
    } finally {
      setSyncing(false)
    }
  }

  const statCards = stats ? [
    {
      label: 'NF-e Recebidas',
      value: stats.total_entrada_mes.toLocaleString('pt-BR'),
      icon: TrendingDown,
      color: 'text-brand-400',
      bg: 'bg-brand-500/10',
      border: 'border-brand-500/20',
    },
    {
      label: 'NF-e Emitidas',
      value: stats.total_saida_mes.toLocaleString('pt-BR'),
      icon: TrendingUp,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
    },
    {
      label: 'Valor Total (Mês)',
      value: formatCurrency(stats.valor_total_mensal),
      icon: FileText,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/20',
    },
    {
      label: 'Canceladas',
      value: stats.total_canceladas.toLocaleString('pt-BR'),
      icon: AlertCircle,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
    },
  ] : []

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Bem-vindo, <span className="text-white font-medium">{empresa?.nome}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {empresa?.status === 'trial' && empresa.trial_expira_em && (
            <span className="badge-yellow">
              <Clock size={11} />
              Trial: {new Date(empresa.trial_expira_em).toLocaleDateString('pt-BR')}
            </span>
          )}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-primary"
          >
            <RefreshCw size={15} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Sincronizando...' : 'Sincronizar SEFAZ'}
          </button>
        </div>
      </div>

      {/* SEFAZ status bar */}
      {sefazStatus && (
        <div className={clsx(
          'flex items-center gap-4 px-4 py-3 rounded-lg border text-sm',
          sefazStatus.certificado_configurado
            ? 'bg-brand-500/5 border-brand-500/20 text-brand-400'
            : 'bg-yellow-500/5 border-yellow-500/20 text-yellow-400'
        )}>
          {sefazStatus.certificado_configurado ? <CheckCircle size={15} /> : <XCircle size={15} />}
          {sefazStatus.certificado_configurado ? (
            <>
              <span>Certificado digital configurado · NSU atual: <strong>{sefazStatus.ultimo_nsu}</strong></span>
              {sefazStatus.ultima_sincronizacao && (
                <span className="text-slate-400 ml-auto text-xs">
                  Última sync: {new Date(sefazStatus.ultima_sincronizacao).toLocaleString('pt-BR')}
                </span>
              )}
            </>
          ) : (
            <span>Configure seu certificado digital para iniciar o monitoramento · <a href="/configuracoes" className="underline">Configurar agora</a></span>
          )}
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-28 skeleton rounded-xl"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card) => (
            <div key={card.label} className="stat-card group">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">{card.label}</span>
                <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center border', card.bg, card.border)}>
                  <card.icon size={15} className={card.color} />
                </div>
              </div>
              <p className="text-2xl font-bold text-white">{card.value}</p>
              <p className="text-xs text-slate-500">Este mês</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      {stats && (
        <div className="card">
          <div className="flex items-center justify-between mb-5">
            <h2 className="section-title">Evolução Mensal de Notas</h2>
            <span className="badge-gray text-xs">Últimos 6 meses</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={stats.grafico_mensal} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22a56c" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22a56c" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
              <XAxis dataKey="mes" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#0f1923', border: '1px solid #1e2d42', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
                itemStyle={{ color: '#22a56c' }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#22a56c"
                strokeWidth={2}
                fill="url(#areaGrad)"
                dot={{ fill: '#22a56c', r: 3 }}
                activeDot={{ r: 5, fill: '#22a56c' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Ver todas as notas', sub: 'Lista completa com filtros', href: '/notas', icon: FileText },
          { label: 'Estatísticas detalhadas', sub: 'Análise fiscal completa', href: '/estatisticas', icon: TrendingUp },
          { label: 'Gerenciar plano', sub: 'Assinatura e cobrança', href: '/planos', icon: AlertCircle },
        ].map((item) => (
          <a key={item.href} href={item.href} className="card-hover flex items-center gap-4 group">
            <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
              <item.icon size={18} className="text-brand-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white group-hover:text-brand-400 transition-colors">{item.label}</p>
              <p className="text-xs text-slate-400 mt-0.5">{item.sub}</p>
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}

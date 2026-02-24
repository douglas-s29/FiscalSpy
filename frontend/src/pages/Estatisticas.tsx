import { useEffect, useState } from 'react'
import api from '../services/api'
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts'
import toast from 'react-hot-toast'

const COLORS = ['#22a56c', '#3b82f6', '#a855f7', '#ef4444', '#f59e0b']

const formatCurrency = (v: number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v)

export default function Estatisticas() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/notas/estatisticas')
      .then(r => setStats(r.data))
      .catch(() => toast.error('Erro ao carregar estatísticas'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex flex-col gap-5 animate-fade-in">
        <h1 className="page-title">Estatísticas</h1>
        <div className="grid grid-cols-2 gap-5">
          {[...Array(4)].map((_, i) => <div key={i} className="card h-64 skeleton rounded-xl" />)}
        </div>
      </div>
    )
  }

  const pieData = [
    { name: 'Entrada', value: stats?.total_entrada_mes || 0 },
    { name: 'Saída', value: stats?.total_saida_mes || 0 },
    { name: 'Canceladas', value: stats?.total_canceladas || 0 },
  ].filter(d => d.value > 0)

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <h1 className="page-title">Estatísticas</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Notas de Entrada (Mês)', value: stats?.total_entrada_mes || 0, suffix: ' notas', color: 'text-brand-400' },
          { label: 'Notas de Saída (Mês)', value: stats?.total_saida_mes || 0, suffix: ' notas', color: 'text-blue-400' },
          { label: 'Valor Total (Mês)', value: formatCurrency(stats?.valor_total_mensal || 0), suffix: '', color: 'text-purple-400' },
          { label: 'Canceladas (Total)', value: stats?.total_canceladas || 0, suffix: ' notas', color: 'text-red-400' },
        ].map(c => (
          <div key={c.label} className="stat-card">
            <p className="text-xs text-slate-400 font-medium">{c.label}</p>
            <p className={`text-2xl font-bold mt-1 ${c.color}`}>{c.value}{c.suffix}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-5">
        {/* Bar chart */}
        <div className="card">
          <h2 className="section-title mb-5">Notas por Mês</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={stats?.grafico_mensal || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
              <XAxis dataKey="mes" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#0f1923', border: '1px solid #1e2d42', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
                itemStyle={{ color: '#22a56c' }}
              />
              <Bar dataKey="total" fill="#22a56c" radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart */}
        <div className="card">
          <h2 className="section-title mb-5">Distribuição por Tipo</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#0f1923', border: '1px solid #1e2d42', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Legend
                  formatter={(value) => <span style={{ color: '#94a3b8', fontSize: '12px' }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
              Sem dados suficientes para o gráfico
            </div>
          )}
        </div>
      </div>

      {/* Additional insights */}
      <div className="card">
        <h2 className="section-title mb-4">Insights do Mês</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-dark-600 rounded-lg p-4 border border-dark-400">
            <p className="text-xs text-slate-400 mb-1">Taxa de Cancelamento</p>
            <p className="text-xl font-bold text-white">
              {stats && (stats.total_entrada_mes + stats.total_saida_mes) > 0
                ? ((stats.total_canceladas / (stats.total_entrada_mes + stats.total_saida_mes)) * 100).toFixed(1)
                : 0}%
            </p>
            <p className="text-xs text-slate-500 mt-1">do total de notas</p>
          </div>
          <div className="bg-dark-600 rounded-lg p-4 border border-dark-400">
            <p className="text-xs text-slate-400 mb-1">Ticket Médio de Entrada</p>
            <p className="text-xl font-bold text-white">
              {stats && stats.total_entrada_mes > 0
                ? formatCurrency(stats.valor_total_mensal / stats.total_entrada_mes)
                : 'R$ 0'}
            </p>
            <p className="text-xs text-slate-500 mt-1">por nota de entrada</p>
          </div>
          <div className="bg-dark-600 rounded-lg p-4 border border-dark-400">
            <p className="text-xs text-slate-400 mb-1">Total de Documentos</p>
            <p className="text-xl font-bold text-white">
              {((stats?.total_entrada_mes || 0) + (stats?.total_saida_mes || 0)).toLocaleString('pt-BR')}
            </p>
            <p className="text-xs text-slate-500 mt-1">neste mês</p>
          </div>
        </div>
      </div>
    </div>
  )
}

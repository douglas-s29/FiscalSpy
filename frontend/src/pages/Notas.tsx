import { useEffect, useState } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'
import { Download, Search, Filter, RefreshCw, FileArchive, FileText, ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

interface Nota {
  id: string
  chave: string
  modelo: string
  tipo: string
  cnpj_emitente: string | null
  cnpj_destinatario: string | null
  valor_total: number | null
  data_emissao: string | null
  status: string
  nsu: number | null
}

const StatusBadge = ({ status }: { status: string }) => {
  const map: Record<string, string> = {
    autorizada: 'badge-green',
    cancelada: 'badge-red',
    denegada: 'badge-yellow',
  }
  return <span className={map[status] || 'badge-gray'}>{status}</span>
}

const TipoBadge = ({ tipo }: { tipo: string }) => (
  <span className={tipo === 'entrada' ? 'badge-blue' : 'badge-gray'}>{tipo}</span>
)

const formatCurrency = (v: number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v)

const formatDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString('pt-BR') : '-'

export default function Notas() {
  const [notas, setNotas] = useState<Nota[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)

  const [filters, setFilters] = useState({
    tipo: '',
    modelo: '',
    status: '',
    data_inicio: '',
    data_fim: '',
  })
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchNotas()
  }, [page, filters])

  const fetchNotas = async () => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (filters.tipo) params.tipo = filters.tipo
      if (filters.modelo) params.modelo = filters.modelo
      if (filters.status) params.status = filters.status
      if (filters.data_inicio) params.data_inicio = filters.data_inicio
      if (filters.data_fim) params.data_fim = filters.data_fim

      const { data } = await api.get('/notas', { params })
      setNotas(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch (err: any) {
      toast.error('Erro ao carregar notas')
    } finally {
      setLoading(false)
    }
  }

  const handleExportExcel = async () => {
    try {
      const resp = await api.get('/notas/exportar', { responseType: 'blob' })
      const url = window.URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'notas_fiscais.xlsx'
      a.click()
      toast.success('Excel exportado!')
    } catch {
      toast.error('Erro ao exportar')
    }
  }

  const handleDownloadLote = async () => {
    setDownloading(true)
    try {
      const resp = await api.get('/notas/download-lote', { responseType: 'blob' })
      const url = window.URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'xmls_fiscais.zip'
      a.click()
      toast.success('Download iniciado!')
    } catch {
      toast.error('Erro ao baixar XMLs')
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadXml = async (id: string, chave: string) => {
    try {
      const resp = await api.get(`/notas/download/${id}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${chave}.xml`
      a.click()
    } catch {
      toast.error('XML não disponível')
    }
  }

  return (
    <div className="flex flex-col gap-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="page-title">Notas Fiscais</h1>
          <p className="text-slate-400 text-sm mt-0.5">{total.toLocaleString('pt-BR')} notas encontradas</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={handleExportExcel} className="btn-secondary text-sm">
            <Download size={15} /> Excel
          </button>
          <button onClick={handleDownloadLote} disabled={downloading} className="btn-secondary text-sm">
            <FileArchive size={15} /> {downloading ? 'Baixando...' : 'ZIP de XMLs'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-48">
          <label className="label">Busca por chave</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input pl-9 py-2 text-sm"
              placeholder="Chave NF-e (44 dígitos)..."
            />
          </div>
        </div>

        <div>
          <label className="label">Tipo</label>
          <select
            value={filters.tipo}
            onChange={e => { setFilters(f => ({ ...f, tipo: e.target.value })); setPage(1) }}
            className="input py-2 text-sm"
          >
            <option value="">Todos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
          </select>
        </div>

        <div>
          <label className="label">Modelo</label>
          <select
            value={filters.modelo}
            onChange={e => { setFilters(f => ({ ...f, modelo: e.target.value })); setPage(1) }}
            className="input py-2 text-sm"
          >
            <option value="">Todos</option>
            <option value="NFe">NF-e</option>
            <option value="CTe">CT-e</option>
          </select>
        </div>

        <div>
          <label className="label">Status</label>
          <select
            value={filters.status}
            onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }}
            className="input py-2 text-sm"
          >
            <option value="">Todos</option>
            <option value="autorizada">Autorizada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>

        <div>
          <label className="label">De</label>
          <input
            type="date"
            value={filters.data_inicio}
            onChange={e => { setFilters(f => ({ ...f, data_inicio: e.target.value })); setPage(1) }}
            className="input py-2 text-sm"
          />
        </div>

        <div>
          <label className="label">Até</label>
          <input
            type="date"
            value={filters.data_fim}
            onChange={e => { setFilters(f => ({ ...f, data_fim: e.target.value })); setPage(1) }}
            className="input py-2 text-sm"
          />
        </div>

        <button onClick={() => { setFilters({ tipo: '', modelo: '', status: '', data_inicio: '', data_fim: '' }); setPage(1) }} className="btn-ghost text-sm">
          <Filter size={14} /> Limpar
        </button>
      </div>

      {/* Table */}
      <div className="table-container">
        {loading ? (
          <div className="p-8 text-center text-slate-400">
            <RefreshCw size={24} className="animate-spin mx-auto mb-3 text-brand-400" />
            Carregando notas...
          </div>
        ) : notas.length === 0 ? (
          <div className="p-12 text-center">
            <FileText size={40} className="mx-auto mb-4 text-slate-600" />
            <p className="text-slate-400 font-medium">Nenhuma nota encontrada</p>
            <p className="text-slate-500 text-sm mt-1">Sincronize com a SEFAZ para importar notas</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Chave</th>
                <th>Modelo</th>
                <th>Tipo</th>
                <th>Emissão</th>
                <th>Emitente</th>
                <th>Destinatário</th>
                <th>Valor</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {notas.map((nota) => (
                <tr key={nota.id}>
                  <td>
                    <span className="font-mono text-xs text-slate-300 truncate max-w-[140px] block">
                      {nota.chave.slice(0, 18)}...
                    </span>
                  </td>
                  <td><span className="badge-gray text-xs">{nota.modelo}</span></td>
                  <td><TipoBadge tipo={nota.tipo} /></td>
                  <td className="text-slate-400 text-xs">{formatDate(nota.data_emissao)}</td>
                  <td className="font-mono text-xs text-slate-400">{nota.cnpj_emitente || '-'}</td>
                  <td className="font-mono text-xs text-slate-400">{nota.cnpj_destinatario || '-'}</td>
                  <td className="font-semibold text-white text-xs">
                    {nota.valor_total ? formatCurrency(nota.valor_total) : '-'}
                  </td>
                  <td><StatusBadge status={nota.status} /></td>
                  <td>
                    <button
                      onClick={() => handleDownloadXml(nota.id, nota.chave)}
                      className="btn-ghost py-1 px-2 text-xs"
                      title="Baixar XML"
                    >
                      <Download size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between px-1">
          <p className="text-sm text-slate-400">
            Página {page} de {pages} · {total} notas
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost py-1.5 px-3 text-sm disabled:opacity-30"
            >
              <ChevronLeft size={15} /> Anterior
            </button>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="btn-ghost py-1.5 px-3 text-sm disabled:opacity-30"
            >
              Próxima <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

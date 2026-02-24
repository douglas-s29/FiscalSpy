import { useState, useEffect, useRef } from 'react'
import { Building2, Shield, Upload, AlertTriangle, CheckCircle, Calendar, User as UserIcon, RefreshCw } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function Configuracoes() {
  const { empresa, fetchEmpresa } = useAuthStore()
  const [nome, setNome] = useState('')
  const [savingNome, setSavingNome] = useState(false)
  const [certFile, setCertFile] = useState<File | null>(null)
  const [certSenha, setCertSenha] = useState('')
  const [uploadingCert, setUploadingCert] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { fetchEmpresa() }, [])

  useEffect(() => {
    if (empresa) setNome(empresa.nome || '')
  }, [empresa?.nome])

  const handleSaveNome = async () => {
    if (!nome.trim()) return toast.error('Informe o nome da empresa')
    setSavingNome(true)
    try {
      await api.put('/empresa/update', { nome })
      await fetchEmpresa()
      toast.success('Nome atualizado!')
    } catch {
      toast.error('Erro ao salvar.')
    } finally {
      setSavingNome(false)
    }
  }

  const handleUploadCert = async () => {
    if (!certFile) return toast.error('Selecione um arquivo .pfx')
    if (!certSenha) return toast.error('Informe a senha do certificado')
    setUploadingCert(true)
    try {
      const form = new FormData()
      form.append('arquivo', certFile)
      form.append('senha', certSenha)
      await api.post('/empresa/upload-certificado', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      toast.success('Certificado enviado e validado!')
      setCertFile(null)
      setCertSenha('')
      await fetchEmpresa()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Erro ao enviar certificado. Verifique o arquivo e a senha.')
    } finally {
      setUploadingCert(false)
    }
  }

  const certOk = empresa?.certificado_configurado
  const nomeTitular = (empresa as any)?.nome_titular
  const validade = (empresa as any)?.validade ? new Date((empresa as any).validade) : null
  const hoje = new Date()
  const certVencido = validade ? validade < hoje : false
  const certVencendoBreve = validade ? (validade.getTime() - hoje.getTime()) < 30 * 24 * 60 * 60 * 1000 : false

  return (
    <div className="p-8 max-w-2xl flex flex-col gap-5">
      <h1 className="text-2xl font-bold text-white">Configurações</h1>

      {/* Dados da empresa */}
      <div className="card">
        <div className="flex items-center gap-2 mb-5">
          <Building2 size={18} className="text-brand-400" />
          <h2 className="text-white font-semibold">Dados da Empresa</h2>
        </div>
        <div className="flex flex-col gap-3">
          <div>
            <label className="label">CNPJ</label>
            <input className="input opacity-60 cursor-not-allowed" value={empresa?.cnpj || ''} readOnly />
          </div>
          <div>
            <label className="label">Nome da Empresa</label>
            <input
              className="input"
              value={nome}
              onChange={e => setNome(e.target.value)}
              placeholder="Nome da empresa"
              onKeyDown={e => e.key === 'Enter' && handleSaveNome()}
            />
          </div>
          <button className="btn-primary w-fit" onClick={handleSaveNome} disabled={savingNome}>
            {savingNome ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>
      </div>

      {/* Certificado Digital */}
      <div className="card">
        <div className="flex items-center gap-2 mb-1">
          <Shield size={18} className="text-brand-400" />
          <h2 className="text-white font-semibold">Certificado Digital A1</h2>
          {certOk && !certVencido && (
            <span className="ml-auto flex items-center gap-1 text-brand-400 text-xs font-semibold">
              <CheckCircle size={13} /> Configurado
            </span>
          )}
          {certVencido && (
            <span className="ml-auto flex items-center gap-1 text-red-400 text-xs font-semibold">
              <AlertTriangle size={13} /> Certificado Vencido
            </span>
          )}
        </div>
        <p className="text-slate-400 text-sm mb-4">
          Upload do certificado A1 (.pfx) para monitoramento via SEFAZ. Criptografado com AES-256.
        </p>

        {/* Card do certificado configurado */}
        {certOk && (
          <div className={`rounded-xl p-4 mb-4 border ${
            certVencido
              ? 'bg-red-500/5 border-red-500/30'
              : certVencendoBreve
              ? 'bg-yellow-500/5 border-yellow-500/30'
              : 'bg-brand-500/5 border-brand-500/20'
          }`}>
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-3">
              Certificado atual
            </p>
            <div className="flex flex-col gap-2">
              <div className="flex items-start gap-2">
                <UserIcon size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-slate-500 mb-0.5">Titular</p>
                  <p className="text-white text-sm font-medium">
                    {nomeTitular || 'Não disponível'}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Calendar size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-slate-500 mb-0.5">Validade</p>
                  <p className={`text-sm font-medium ${certVencido ? 'text-red-400' : certVencendoBreve ? 'text-yellow-400' : 'text-white'}`}>
                    {validade
                      ? validade.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
                      : 'Não disponível'}
                    {certVencido && ' — VENCIDO'}
                    {!certVencido && certVencendoBreve && ' — Vence em breve!'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Upload zone */}
        <p className="text-xs text-slate-500 mb-2 font-medium">
          {certOk ? 'Substituir certificado:' : 'Enviar certificado:'}
        </p>
        <div
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all mb-3 ${
            certFile
              ? 'border-brand-500/70 bg-brand-500/5'
              : 'border-dark-400 hover:border-dark-300 hover:bg-dark-700/50'
          }`}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => {
            e.preventDefault()
            const f = e.dataTransfer.files[0]
            if (f?.name.toLowerCase().endsWith('.pfx')) setCertFile(f)
            else toast.error('Apenas arquivos .pfx são aceitos')
          }}
        >
          <Upload size={18} className="mx-auto mb-2 text-slate-400" />
          {certFile ? (
            <p className="text-brand-400 text-sm font-semibold">{certFile.name}</p>
          ) : (
            <>
              <p className="text-slate-300 text-sm">Arraste o arquivo .pfx ou clique para selecionar</p>
              <p className="text-slate-500 text-xs mt-1">Apenas certificados A1 no formato .pfx</p>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".pfx"
            className="hidden"
            onChange={e => setCertFile(e.target.files?.[0] || null)}
          />
        </div>

        <div className="mb-4">
          <label className="label">Senha do Certificado</label>
          <input
            type="password"
            className="input"
            value={certSenha}
            onChange={e => setCertSenha(e.target.value)}
            placeholder="Senha do arquivo .pfx"
            onKeyDown={e => e.key === 'Enter' && handleUploadCert()}
          />
        </div>

        <button
          className="btn-primary w-fit flex items-center gap-2"
          onClick={handleUploadCert}
          disabled={uploadingCert || !certFile}
        >
          {uploadingCert ? (
            <><RefreshCw size={14} className="animate-spin" /> Validando...</>
          ) : (
            <><Upload size={14} /> Enviar Certificado</>
          )}
        </button>
      </div>

      {/* Zona de risco */}
      <div className="card border-red-500/20 bg-red-500/5">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={18} className="text-red-400" />
          <h2 className="text-red-400 font-semibold">Zona de Risco</h2>
        </div>
        <p className="text-slate-400 text-sm mb-3">Estas ações são irreversíveis. Tenha certeza do que está fazendo.</p>
        <button className="px-4 py-2 rounded-lg border border-red-500/40 text-red-400 text-sm hover:bg-red-500/10 transition-colors">
          Solicitar exclusão da conta
        </button>
      </div>
    </div>
  )
}

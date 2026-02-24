import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Radar, Building2, User, Mail, Lock, CreditCard } from 'lucide-react'

export default function Register() {
  const [form, setForm] = useState({
    nome_empresa: '',
    cnpj: '',
    nome_usuario: '',
    email: '',
    senha: '',
  })
  const [loading, setLoading] = useState(false)
  const { register } = useAuthStore()
  const navigate = useNavigate()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.name === 'cnpj'
      ? e.target.value.replace(/\D/g, '').slice(0, 14)
      : e.target.value
    setForm(f => ({ ...f, [e.target.name]: val }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.cnpj.length !== 14) {
      toast.error('CNPJ deve ter 14 dígitos')
      return
    }
    setLoading(true)
    try {
      await register(form)
      toast.success('Conta criada! Aproveite 7 dias grátis.')
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Erro ao criar conta')
    } finally {
      setLoading(false)
    }
  }

  const fields = [
    { name: 'nome_empresa', label: 'Nome da Empresa', icon: Building2, type: 'text', placeholder: 'Empresa LTDA' },
    { name: 'cnpj', label: 'CNPJ (apenas números)', icon: CreditCard, type: 'text', placeholder: '00000000000000' },
    { name: 'nome_usuario', label: 'Seu Nome', icon: User, type: 'text', placeholder: 'João Silva' },
    { name: 'email', label: 'Email', icon: Mail, type: 'email', placeholder: 'joao@empresa.com' },
    { name: 'senha', label: 'Senha', icon: Lock, type: 'password', placeholder: '••••••••' },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-900 px-4 py-12 relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-brand-500/5 blur-3xl pointer-events-none"></div>

      <div className="relative w-full max-w-md animate-slide-up">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Radar size={20} className="text-white" />
            </div>
            <span className="font-bold text-white text-xl">FiscalSpy</span>
          </Link>
          <h1 className="text-2xl font-bold text-white mt-6">Crie sua conta</h1>
          <p className="text-slate-400 mt-1 text-sm">7 dias grátis · Sem cartão de crédito</p>
        </div>

        <div className="card border-dark-400 shadow-2xl shadow-black/30">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {fields.map((f) => (
              <div key={f.name}>
                <label className="label">{f.label}</label>
                <div className="relative">
                  <f.icon size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type={f.type}
                    name={f.name}
                    value={(form as any)[f.name]}
                    onChange={handleChange}
                    className="input pl-10"
                    placeholder={f.placeholder}
                    required
                    minLength={f.name === 'senha' ? 8 : undefined}
                  />
                </div>
              </div>
            ))}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3 mt-2">
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Criando conta...
                </span>
              ) : 'Criar conta gratuita'}
            </button>
          </form>

          <div className="mt-5 pt-5 border-t border-dark-500 text-center">
            <p className="text-sm text-slate-400">
              Já tem conta?{' '}
              <Link to="/login" className="text-brand-400 font-semibold hover:text-brand-300 transition-colors">
                Entrar
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

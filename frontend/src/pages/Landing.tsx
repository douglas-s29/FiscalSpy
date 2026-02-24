import { Link } from 'react-router-dom'
import { Radar, Shield, Zap, Download, ChevronRight, Check, Eye, Bell, FileText, TrendingUp, Code, Webhook, Key } from 'lucide-react'

const features = [
  { icon: Eye, title: 'Monitoramento em Tempo Real', desc: 'Todas as NF-e e CT-e emitidas contra ou por seu CNPJ capturadas automaticamente via SEFAZ.' },
  { icon: Download, title: 'Download Automático de XML', desc: 'XMLs baixados e organizados automaticamente. Export em lote com um clique.' },
  { icon: Bell, title: 'Alertas Inteligentes', desc: 'Notificações instantâneas para cancelamentos, cartas de correção e eventos fiscais.' },
  { icon: Shield, title: 'Manifestação Automática', desc: 'Manifeste automaticamente suas notas de entrada conforme legislação vigente.' },
  { icon: TrendingUp, title: 'Análise Fiscal Avançada', desc: 'Dashboards e gráficos detalhados para análise de entradas, saídas e tendências.' },
  { icon: Key, title: 'Segurança Máxima', desc: 'Certificados digitais criptografados com AES-256. Dados protegidos em servidores seguros.' },
]

const plans = [
  { name: 'Starter', price: 97, description: 'Ideal para MEI e pequenas empresas', features: ['1 CNPJ monitorado', 'Até 1.000 notas/mês', 'Download de XML', 'Suporte por email'], highlighted: false },
  { name: 'Business', price: 197, description: 'Para empresas em crescimento', features: ['3 CNPJs monitorados', 'Notas ilimitadas', 'Manifestação automática', 'Export Excel/ZIP', 'Suporte prioritário', 'API de integração'], highlighted: true },
  { name: 'Enterprise', price: 497, description: 'Para grupos empresariais', features: ['CNPJs ilimitados', 'Volume ilimitado', 'Tudo do Business', 'SLA 99.9%', 'Gerente de conta', 'Onboarding dedicado'], highlighted: false },
]

const stats = [
  { value: '12M+', label: 'Notas monitoradas' },
  { value: '2.500+', label: 'Empresas ativas' },
  { value: '99.9%', label: 'Uptime garantido' },
  { value: '< 5min', label: 'Latência de captura' },
]

const integracoes = [
  { icon: Webhook, title: 'Webhook em Tempo Real', desc: 'Receba notificações instantâneas no seu sistema quando uma nova nota for capturada. Configure sua URL e comece a receber eventos.' },
  { icon: Code, title: 'API REST Completa', desc: 'API documentada com Swagger/OpenAPI. Integre o FiscalSpy em qualquer sistema com autenticação JWT e endpoints padronizados.' },
  { icon: FileText, title: 'Export Automatizado', desc: 'Exporte XMLs, planilhas Excel e relatórios em PDF automaticamente. Integre com seu ERP ou sistema contábil.' },
  { icon: Shield, title: 'Autenticação Segura', desc: 'OAuth2 com JWT, refresh tokens e rate limiting. Sua integração sempre segura e dentro das melhores práticas.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-dark-900 overflow-x-hidden">
      {/* Header */}
      <header className="fixed top-0 inset-x-0 z-50">
        <div className="glass border-b border-dark-500/50 px-6 py-3.5">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                <Radar size={16} className="text-white" />
              </div>
              <span className="font-bold text-white text-lg">FiscalSpy</span>
            </div>
            <nav className="hidden md:flex items-center gap-8">
              <a href="#funcionalidades" className="text-sm text-slate-400 hover:text-white transition-colors">Funcionalidades</a>
              <a href="#planos" className="text-sm text-slate-400 hover:text-white transition-colors">Planos</a>
              <a href="#integracao" className="text-sm text-slate-400 hover:text-white transition-colors">Integração</a>
            </nav>
            <div className="flex items-center gap-3">
              <Link to="/login" className="text-sm text-slate-300 hover:text-white transition-colors">Entrar</Link>
              <Link to="/cadastro" className="btn-primary text-sm py-2">
                Teste grátis <ChevronRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative pt-36 pb-24 px-6 overflow-hidden">
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full bg-brand-500/5 blur-3xl pointer-events-none"></div>
        <div className="absolute inset-0 bg-[linear-gradient(rgba(22,38,58,0.3)_1px,transparent_1px),linear-gradient(90deg,rgba(22,38,58,0.3)_1px,transparent_1px)] bg-[size:60px_60px] pointer-events-none"></div>

        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-sm font-medium mb-8">
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse"></span>
            Monitoramento fiscal em tempo real via SEFAZ
          </div>
          <h1 className="text-5xl md:text-7xl font-bold text-white leading-tight tracking-tight mb-6">
            Sua inteligência fiscal,<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-brand-600">trabalhando 24/7</span>
          </h1>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Capture automaticamente todas as NF-e e CT-e emitidas contra seu CNPJ diretamente da SEFAZ. Download de XML, eventos fiscais e manifestação — tudo automatizado.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/cadastro" className="btn-primary text-base px-8 py-3.5 w-full sm:w-auto">
              Começar 7 dias grátis <ChevronRight size={16} />
            </Link>
            <a href="#funcionalidades" className="btn-secondary text-base px-8 py-3.5 w-full sm:w-auto">
              Ver funcionalidades
            </a>
          </div>
          <p className="mt-5 text-sm text-slate-500">Sem cartão de crédito · Cancele quando quiser</p>
        </div>

        {/* Dashboard preview */}
        <div className="relative max-w-5xl mx-auto mt-20">
          <div className="rounded-2xl border border-dark-500 bg-dark-800 overflow-hidden shadow-2xl shadow-black/50">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-dark-500 bg-dark-700">
              <div className="w-3 h-3 rounded-full bg-red-500/60"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/60"></div>
              <div className="w-3 h-3 rounded-full bg-brand-500/60"></div>
              <span className="ml-3 text-xs text-slate-500 font-mono">fiscalspy.app/dashboard</span>
            </div>
            <div className="p-6 grid grid-cols-3 gap-4">
              {[
                { label: 'NF-e Recebidas', value: '1.284', change: '+23%', color: 'text-brand-400' },
                { label: 'Valor Total Entrada', value: 'R$ 847K', change: '+12%', color: 'text-blue-400' },
                { label: 'Notas Canceladas', value: '7', change: '-45%', color: 'text-red-400' },
              ].map((s) => (
                <div key={s.label} className="card">
                  <p className="text-xs text-slate-500">{s.label}</p>
                  <p className="text-2xl font-bold text-white mt-1">{s.value}</p>
                  <p className={`text-xs mt-1 ${s.color}`}>{s.change} vs mês anterior</p>
                </div>
              ))}
            </div>
            <div className="px-6 pb-6">
              <div className="card h-24 flex items-center justify-center">
                <div className="flex gap-1 items-end h-14">
                  {[40, 60, 45, 80, 65, 90, 75, 100, 70, 85, 60, 95].map((h, i) => (
                    <div key={i} className="w-5 rounded-sm bg-gradient-to-t from-brand-700 to-brand-500 opacity-80" style={{ height: `${h}%` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="absolute -inset-1 bg-gradient-to-b from-transparent via-transparent to-dark-900 pointer-events-none rounded-2xl"></div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 border-y border-dark-500 bg-dark-800/50">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-bold text-white">{s.value}</p>
              <p className="text-sm text-slate-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="funcionalidades" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Tudo que seu departamento fiscal precisa</h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">Uma plataforma completa, integrada diretamente com a Receita Federal via SEFAZ.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => (
              <div key={f.title} className="card-hover group">
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4 group-hover:bg-brand-500/20 transition-colors">
                  <f.icon size={20} className="text-brand-400" />
                </div>
                <h3 className="text-white font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Plans */}
      <section id="planos" className="py-24 px-6 bg-dark-800/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Planos para todos os tamanhos</h2>
            <p className="text-slate-400 text-lg">7 dias grátis em qualquer plano. Sem compromisso.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan, idx) => (
              <div key={plan.name} className={`relative rounded-xl border p-6 flex flex-col ${plan.highlighted ? 'bg-brand-500/5 border-brand-500/30 shadow-xl shadow-brand-500/10' : 'bg-dark-700 border-dark-500'}`}>
                {plan.highlighted && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-brand-500 text-white text-xs font-bold rounded-full">MAIS POPULAR</div>
                )}
                <div className="mb-5">
                  <h3 className="text-xl font-bold text-white">{plan.name}</h3>
                  <p className="text-slate-400 text-sm mt-1">{plan.description}</p>
                </div>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-white">R$ {plan.price}</span>
                  <span className="text-slate-400 text-sm">/mês</span>
                </div>
                <ul className="flex-1 flex flex-col gap-2.5 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2.5 text-sm text-slate-300">
                      <Check size={14} className="text-brand-400 flex-shrink-0" />{f}
                    </li>
                  ))}
                </ul>
                <Link to="/cadastro" className={plan.highlighted ? 'btn-primary text-center' : 'btn-secondary text-center'}>
                  Começar grátis
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integração */}
      <section id="integracao" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-sm font-medium mb-6">
              <Code size={14} /> API & Integrações
            </div>
            <h2 className="text-4xl font-bold text-white mb-4">Integre com qualquer sistema</h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">API REST documentada, webhooks em tempo real e SDKs para as principais linguagens.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-5 mb-12">
            {integracoes.map((item) => (
              <div key={item.title} className="card-hover group flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-500/20 transition-colors">
                  <item.icon size={18} className="text-brand-400" />
                </div>
                <div>
                  <h3 className="text-white font-semibold mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Code example */}
          <div className="card border-dark-400 bg-dark-800">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500/60"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/60"></div>
              <div className="w-3 h-3 rounded-full bg-brand-500/60"></div>
              <span className="ml-2 text-xs text-slate-500 font-mono">exemplo de integração</span>
            </div>
            <pre className="text-sm font-mono text-slate-300 overflow-x-auto">
{`// Buscar notas fiscais via API
const response = await fetch('https://api.fiscalspy.app/api/notas', {
  headers: {
    'Authorization': 'Bearer SEU_TOKEN_JWT',
    'Content-Type': 'application/json'
  }
});

const { items, total } = await response.json();
console.log(\`\${total} notas encontradas\`);`}
            </pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 text-center bg-dark-800/30">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-bold text-white mb-4">Pronto para ter controle total?</h2>
          <p className="text-slate-400 text-lg mb-8">Junte-se a mais de 2.500 empresas que monitoram suas notas fiscais com o FiscalSpy.</p>
          <Link to="/cadastro" className="btn-primary text-base px-10 py-4">
            Criar conta gratuita <ChevronRight size={16} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-dark-500">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Radar size={16} className="text-brand-400" />
            <span className="font-semibold text-white">FiscalSpy</span>
          </div>
          <p className="text-sm text-slate-500">© 2025 FiscalSpy. Todos os direitos reservados.</p>
          <div className="flex gap-6 text-sm text-slate-500">
            <a href="#" className="hover:text-white transition-colors">Privacidade</a>
            <a href="#" className="hover:text-white transition-colors">Termos</a>
            <a href="#" className="hover:text-white transition-colors">Suporte</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

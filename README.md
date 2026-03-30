# ⚡ TechOS Pro — Sistema para Lojas de Celular e Informática
**Criado por Robinho — Orange Tech Solutions**

---

## 📁 Estrutura do Projeto

```
techos-pro/
├── app.py                        ← Backend Flask completo
├── requirements.txt
└── templates/
    ├── base.html                 ← Layout base (sidebar dark)
    ├── login.html
    ├── registrar.html
    ├── assinar.html              ← Tela de assinatura PIX
    ├── painel.html               ← Dashboard
    ├── clientes.html
    ├── form_cliente.html
    ├── os_lista.html
    ├── form_os.html
    ├── os_itens.html
    ├── imprimir_os.html          ← Impressão térmica OS (80mm/50mm)
    ├── acessorios.html           ← Películas, Capinhas, etc.
    ├── form_acessorio.html
    ├── estoque.html
    ├── form_estoque.html
    ├── encomendas.html
    ├── form_encomenda.html
    ├── pdv.html                  ← Ponto de Venda
    ├── vendas.html
    ├── cupom_venda.html          ← Cupom térmico (80mm/50mm)
    ├── financeiro.html
    ├── relatorios.html
    ├── categorias.html
    └── configuracoes.html
```

---

## 🚀 Deploy no Render

### 1. PostgreSQL
- Criar banco: **techos-db** → Free → copiar **Internal Database URL**

### 2. Web Service
- Conectar repo `techos-pro`
- Build: `pip install --upgrade pip && pip install -r requirements.txt`
- Start: `gunicorn app:app`

### 3. Variáveis de Ambiente

| Variável | Valor |
|---|---|
| `SECRET_KEY` | `techos2024orange` |
| `ADMIN_TOKEN` | `robinho_admin_2024` |
| `API_TOKEN` | `orangetech_api_2024` |
| `MP_PUBLIC_KEY` | `TEST-c386fde1-e1a2-45a1-99dd-0a5c5178d84f` |
| `MP_ACCESS_TOKEN` | `TEST-4564359250372854-032110-c05486855621788139e407428bf8f299-2584732465` |
| `DATABASE_URL` | *(Internal URL do banco)* |
| `PYTHON_VERSION` | `3.11.9` |

---

## 🏠 Admin Hub — Adicionar TechOS

Em `orangetech-admin/app.py`, na lista `SISTEMAS`:

```python
{
    "id": "techos",
    "nome": "TechOS Pro",
    "emoji": "⚡",
    "cor": "#00d4ff",
    "url": os.environ.get("URL_TECHOS", "https://techos-pro.onrender.com"),
    "preco": 89.90,
    "ativo": True
},
```

Adicionar variável `URL_TECHOS` no Render do Admin Hub!

---

## 📱 Módulos do Sistema

| Módulo | Descrição |
|---|---|
| 🔧 **OS** | Ordens de Serviço com itens, laudo, impressão 80/50mm |
| 👥 **Clientes** | Cadastro completo CPF/CNPJ |
| 📱 **Acessórios** | Películas (3D/5D/9D/Gel/Cerâmica/Privativa) + Capinhas por marca/modelo |
| 🗄️ **Estoque** | Peças, Placas, Sub-placas, categorias customizáveis |
| 🛒 **PDV** | Venda com Dinheiro/Pix/Crédito/Débito, cupom térmico |
| 📦 **Encomendas** | Entrada adiantada/parcial, múltiplas formas de pagamento |
| 💰 **Financeiro** | Receitas, despesas, saldo |
| 📈 **Relatórios** | OS por status, top peças, acessórios, financeiro |
| ⚙️ **Config** | Dados da loja para cabeçalho dos cupons, tamanho impressora |

---

## 🖨️ Impressão Térmica

- **80mm** — padrão (maioria das impressoras não fiscais)
- **50mm** — compacto
- A largura é salva nas configurações da loja
- URL de impressão: `/os/imprimir/<id>?l=80mm`
- Cupom de venda: `/vendas/cupom/<id>?l=80mm`
- Adicione `?print=1` para imprimir automaticamente ao abrir

---

## 🔒 Sistema de Licença

- **Trial**: 1 hora após cadastro
- **Pós-trial**: Tela de assinatura com QR Code PIX (Mercado Pago)
- **Webhook**: `/webhook/mp` — ativa automaticamente ao receber pagamento aprovado
- **Admin Hub**: pode liberar/bloquear/estender trial via API

---

## 💳 Integração Mercado Pago

O sistema já está integrado. Para produção:
1. Troque os tokens TEST por produção no Render
2. Configure o webhook no painel do Mercado Pago apontando para:
   `https://seu-dominio.onrender.com/webhook/mp`

---

## 📞 Suporte
**Orange Tech Solutions** — Robinho
WhatsApp: (41) 9xxxx-xxxx

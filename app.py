"""
╔══════════════════════════════════════════════════════════════╗
║         ⚡  TECHOS PRO  — Sistema para Lojas de Celular     ║
║   Flask + PostgreSQL + Mercado Pago PIX                      ║
║   Trial 1h → PIX → 30 dias de acesso                        ║
║   Criado por Robinho — Orange Tech Solutions                 ║
╚══════════════════════════════════════════════════════════════╝
"""
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify, Response)
from functools import wraps
import psycopg
import psycopg.rows
import os, datetime, hashlib, secrets, json
import requests as http_req

app = Flask(__name__)
app.secret_key    = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DATABASE_URL      = os.environ.get("DATABASE_URL", "")
MP_ACCESS_TOKEN   = os.environ.get("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY     = os.environ.get("MP_PUBLIC_KEY", "")
ADMIN_TOKEN       = os.environ.get("ADMIN_TOKEN", "robinho_admin_2024")
API_TOKEN         = os.environ.get("API_TOKEN", "orangetech_api_2024")
PRECO_MENSAL      = 89.90
TRIAL_HORAS       = 1

# ─────────────────────────────────────────────────────────────
# BANCO DE DADOS
# ─────────────────────────────────────────────────────────────
def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id               SERIAL PRIMARY KEY,
                nome             TEXT NOT NULL,
                usuario          TEXT UNIQUE NOT NULL,
                senha_hash       TEXT NOT NULL,
                plano            TEXT DEFAULT 'trial',
                trial_inicio     TIMESTAMP DEFAULT NOW(),
                plano_valido_ate TIMESTAMP,
                -- config da loja
                loja_nome        TEXT,
                loja_cnpj        TEXT,
                loja_tel         TEXT,
                loja_end         TEXT,
                loja_cidade      TEXT,
                loja_uf          TEXT,
                loja_logo        TEXT,
                impressora       TEXT DEFAULT '80mm',
                criado_em        DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS clientes (
                id         SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                nome       TEXT NOT NULL,
                telefone   TEXT,
                whatsapp   TEXT,
                email      TEXT,
                cpfcnpj    TEXT,
                tipo       TEXT DEFAULT 'Pessoa Física',
                endereco   TEXT,
                cidade     TEXT,
                uf         TEXT,
                obs        TEXT,
                criado_em  DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS categorias_produto (
                id         SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                nome       TEXT NOT NULL,
                tipo       TEXT DEFAULT 'produto'
            );

            CREATE TABLE IF NOT EXISTS produtos (
                id            SERIAL PRIMARY KEY,
                empresa_id    INT REFERENCES empresas(id) ON DELETE CASCADE,
                codigo        TEXT,
                descricao     TEXT NOT NULL,
                categoria     TEXT,
                categoria_id  INT REFERENCES categorias_produto(id) ON DELETE SET NULL,
                marca         TEXT,
                modelo_compativel TEXT,
                unidade       TEXT DEFAULT 'UN',
                custo         NUMERIC DEFAULT 0,
                margem        NUMERIC DEFAULT 30,
                preco_venda   NUMERIC DEFAULT 0,
                tipo          TEXT DEFAULT 'Produto',
                aplicacao     TEXT,
                obs           TEXT,
                criado_em     DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS estoque (
                id          SERIAL PRIMARY KEY,
                empresa_id  INT REFERENCES empresas(id) ON DELETE CASCADE,
                produto_id  INT REFERENCES produtos(id) ON DELETE SET NULL,
                codigo      TEXT,
                descricao   TEXT NOT NULL,
                categoria   TEXT,
                localizacao TEXT,
                fornecedor  TEXT,
                qtd         NUMERIC DEFAULT 0,
                qtd_min     NUMERIC DEFAULT 0,
                custo       NUMERIC DEFAULT 0,
                preco_venda NUMERIC DEFAULT 0,
                obs         TEXT,
                atualizado  DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS acessorios (
                id                SERIAL PRIMARY KEY,
                empresa_id        INT REFERENCES empresas(id) ON DELETE CASCADE,
                tipo              TEXT NOT NULL,
                subtipo           TEXT,
                marca_aparelho    TEXT,
                modelo_aparelho   TEXT,
                descricao         TEXT,
                codigo            TEXT,
                custo             NUMERIC DEFAULT 0,
                preco_venda       NUMERIC DEFAULT 0,
                qtd               NUMERIC DEFAULT 0,
                qtd_min           NUMERIC DEFAULT 1,
                fornecedor        TEXT,
                cor               TEXT,
                obs               TEXT,
                criado_em         DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS os (
                id           SERIAL PRIMARY KEY,
                empresa_id   INT REFERENCES empresas(id) ON DELETE CASCADE,
                numero       TEXT,
                data_abert   DATE DEFAULT CURRENT_DATE,
                cliente_id   INT REFERENCES clientes(id) ON DELETE SET NULL,
                cliente      TEXT,
                aparelho     TEXT,
                imei         TEXT,
                defeito      TEXT,
                senha_apar   TEXT,
                acessorios   TEXT,
                tecnico      TEXT,
                servicos     TEXT,
                laudo        TEXT,
                status       TEXT DEFAULT 'Aguardando',
                total        NUMERIC DEFAULT 0,
                desconto     NUMERIC DEFAULT 0,
                pagto        TEXT,
                pago         TEXT DEFAULT 'Não',
                data_prazo   DATE,
                obs          TEXT,
                criado_em    DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS os_itens (
                id          SERIAL PRIMARY KEY,
                empresa_id  INT REFERENCES empresas(id) ON DELETE CASCADE,
                os_id       INT REFERENCES os(id) ON DELETE CASCADE,
                estoque_id  INT REFERENCES estoque(id) ON DELETE SET NULL,
                descricao   TEXT NOT NULL,
                qtd         NUMERIC DEFAULT 1,
                valor_unit  NUMERIC DEFAULT 0,
                subtotal    NUMERIC DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS encomendas (
                id           SERIAL PRIMARY KEY,
                empresa_id   INT REFERENCES empresas(id) ON DELETE CASCADE,
                cliente_id   INT REFERENCES clientes(id) ON DELETE SET NULL,
                cliente      TEXT NOT NULL,
                produto      TEXT NOT NULL,
                total        NUMERIC DEFAULT 0,
                entrada      NUMERIC DEFAULT 0,
                fpgto_entrada TEXT,
                fpgto_saldo  TEXT DEFAULT 'A definir',
                data_prazo   DATE,
                status       TEXT DEFAULT 'aguardando',
                obs          TEXT,
                criado_em    DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS vendas (
                id         SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                cliente_id INT REFERENCES clientes(id) ON DELETE SET NULL,
                cliente    TEXT,
                total      NUMERIC DEFAULT 0,
                desconto   NUMERIC DEFAULT 0,
                pagto      TEXT,
                parcelas   INT DEFAULT 1,
                status     TEXT DEFAULT 'finalizada',
                obs        TEXT,
                criado_em  DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS venda_itens (
                id          SERIAL PRIMARY KEY,
                empresa_id  INT REFERENCES empresas(id) ON DELETE CASCADE,
                venda_id    INT REFERENCES vendas(id) ON DELETE CASCADE,
                estoque_id  INT REFERENCES estoque(id) ON DELETE SET NULL,
                acessorio_id INT REFERENCES acessorios(id) ON DELETE SET NULL,
                descricao   TEXT NOT NULL,
                qtd         NUMERIC DEFAULT 1,
                valor_unit  NUMERIC DEFAULT 0,
                subtotal    NUMERIC DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS financeiro (
                id         SERIAL PRIMARY KEY,
                empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
                data       DATE DEFAULT CURRENT_DATE,
                tipo       TEXT,
                categoria  TEXT,
                descricao  TEXT,
                valor      NUMERIC DEFAULT 0,
                pagto      TEXT,
                pago       TEXT DEFAULT 'Sim',
                obs        TEXT
            );

            CREATE TABLE IF NOT EXISTS pagamentos (
                id              SERIAL PRIMARY KEY,
                empresa_id      INT REFERENCES empresas(id) ON DELETE CASCADE,
                mp_payment_id   TEXT,
                valor           NUMERIC DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                criado_em       TIMESTAMP DEFAULT NOW(),
                pago_em         TIMESTAMP
            );
            """)
            # Migrations seguras
            for sql in [
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_nome TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_cnpj TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_tel TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_end TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_cidade TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS loja_uf TEXT",
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS impressora TEXT DEFAULT '80mm'",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS numero TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS imei TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS defeito TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS laudo TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS aparelho TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS senha_apar TEXT",
                "ALTER TABLE os ADD COLUMN IF NOT EXISTS cliente_id INT",
                "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco_venda NUMERIC DEFAULT 0",
                "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS modelo_compativel TEXT",
                "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS categoria_id INT",
                "ALTER TABLE estoque ADD COLUMN IF NOT EXISTS produto_id INT",
                "ALTER TABLE estoque ADD COLUMN IF NOT EXISTS preco_venda NUMERIC DEFAULT 0",
            ]:
                try:
                    c.execute(sql)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def hash_senha(s): return hashlib.sha256(s.encode()).hexdigest()

def fmtR(v):
    try:    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

def stock_status(qtd, qtd_min):
    try:
        q,m = float(qtd or 0), float(qtd_min or 0)
        if q <= 0:       return "Sem Estoque"
        if q <= m:       return "Crítico"
        if q <= m*1.5:   return "Baixo"
        return "OK"
    except: return ""

def next_os_num(empresa_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as n FROM os WHERE empresa_id=%s", (empresa_id,))
            n = c.fetchone()["n"]
    return str(n + 1).zfill(4)

# ─────────────────────────────────────────────────────────────
# CONTROLE DE PLANO
# ─────────────────────────────────────────────────────────────
def get_empresa_status(empresa_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM empresas WHERE id=%s", (empresa_id,))
            emp = c.fetchone()
    if not emp: return "expirado"
    agora = datetime.datetime.now()
    if emp["plano"] == "ativo" and emp["plano_valido_ate"]:
        return "ativo" if emp["plano_valido_ate"] > agora else "expirado"
    if emp["plano"] == "trial" and emp["trial_inicio"]:
        if emp.get("plano_valido_ate") and emp["plano_valido_ate"] > agora:
            mins = int((emp["plano_valido_ate"] - agora).total_seconds() / 60)
            return f"trial:{mins}"
        fim = emp["trial_inicio"] + datetime.timedelta(hours=TRIAL_HORAS)
        if agora < fim:
            mins = int((fim - agora).total_seconds() / 60)
            return f"trial:{mins}"
    return "expirado"

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if "empresa_id" not in session:
            return redirect(url_for("login"))
        if get_empresa_status(session["empresa_id"]) == "expirado":
            return redirect(url_for("assinar"))
        return f(*a, **kw)
    return dec

def api_auth():
    return request.headers.get("X-API-Token","") == API_TOKEN

# ─────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def login():
    if "empresa_id" in session: return redirect(url_for("painel"))
    erro = None
    if request.method == "POST":
        u = request.form.get("usuario","").strip()
        s = request.form.get("senha","").strip()
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM empresas WHERE usuario=%s AND senha_hash=%s",
                          (u, hash_senha(s)))
                emp = c.fetchone()
        if emp:
            session["empresa_id"]   = emp["id"]
            session["empresa_nome"] = emp["nome"]
            if get_empresa_status(emp["id"]) == "expirado":
                return redirect(url_for("assinar"))
            return redirect(url_for("painel"))
        erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/registrar", methods=["GET","POST"])
def registrar():
    erro = None
    if request.method == "POST":
        nome    = request.form.get("nome","").strip()
        usuario = request.form.get("usuario","").strip()
        senha   = request.form.get("senha","").strip()
        try:
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("""
                        INSERT INTO empresas (nome,usuario,senha_hash,plano,trial_inicio,loja_nome)
                        VALUES (%s,%s,%s,'trial',NOW(),%s)
                    """, (nome, usuario, hash_senha(senha), nome))
            flash("Conta criada! Você tem acesso gratuito por 1 hora. 🚀","success")
            return redirect(url_for("login"))
        except psycopg.errors.UniqueViolation:
            erro = "Usuário já existe."
        except Exception as e:
            erro = f"Erro: {e}"
    return render_template("registrar.html", erro=erro)

# ─────────────────────────────────────────────────────────────
# ASSINATURA / PIX (Mercado Pago)
# ─────────────────────────────────────────────────────────────
@app.route("/assinar")
def assinar():
    if "empresa_id" not in session: return redirect(url_for("login"))
    return render_template("assinar.html",
        empresa_nome=session.get("empresa_nome",""),
        preco=fmtR(PRECO_MENSAL), mp_public_key=MP_PUBLIC_KEY)

@app.route("/gerar_pix", methods=["POST"])
def gerar_pix():
    if "empresa_id" not in session: return jsonify({"erro":"Não autorizado"}),401
    eid  = session["empresa_id"]
    nome = session.get("empresa_nome","")
    base = request.host_url.rstrip("/")
    payload = {
        "transaction_amount": PRECO_MENSAL,
        "description": f"TechOS Pro — 30 dias — {nome}",
        "payment_method_id": "pix",
        "payer": {"email": f"empresa_{eid}@techos.pro", "first_name": nome[:20], "last_name": "Pro"},
        "notification_url": f"{base}/webhook/mp",
        "external_reference": str(eid),
        "date_of_expiration": (datetime.datetime.now()+datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
    }
    try:
        resp = http_req.post("https://api.mercadopago.com/v1/payments",
            json=payload,
            headers={
                "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
                "X-Idempotency-Key": f"techos_{eid}_{int(datetime.datetime.now().timestamp())}",
                "Content-Type": "application/json"
            }, timeout=15)
        data = resp.json()
        if resp.status_code in (200,201):
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("INSERT INTO pagamentos (empresa_id,mp_payment_id,valor,status) VALUES (%s,%s,%s,'pending')",
                              (eid, str(data.get("id")), PRECO_MENSAL))
            pix = data.get("point_of_interaction",{}).get("transaction_data",{})
            return jsonify({
                "qr_code":        pix.get("qr_code",""),
                "qr_code_base64": pix.get("qr_code_base64",""),
                "payment_id":     data.get("id"),
                "status":         data.get("status")
            })
        return jsonify({"erro": data.get("message","Erro ao gerar PIX")}),400
    except Exception as e:
        return jsonify({"erro": str(e)}),500

@app.route("/verificar_pagamento/<int:payment_id>")
def verificar_pagamento(payment_id):
    if "empresa_id" not in session: return jsonify({"status":"erro"}),401
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT status FROM pagamentos WHERE mp_payment_id=%s AND empresa_id=%s",
                      (str(payment_id), session["empresa_id"]))
            p = c.fetchone()
    return jsonify({"status":"aprovado" if p and p["status"]=="approved" else "pendente"})

@app.route("/webhook/mp", methods=["POST"])
def webhook_mp():
    data = request.get_json(silent=True) or {}
    tipo = data.get("type") or data.get("action","")
    payment_id = None
    if "payment" in tipo:
        payment_id = data.get("data",{}).get("id")
    if not payment_id: return jsonify({"ok":True}),200
    try:
        resp = http_req.get(f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization":f"Bearer {MP_ACCESS_TOKEN}"}, timeout=10)
        pd = resp.json()
    except: return jsonify({"ok":True}),200
    status = pd.get("status")
    eid_s  = pd.get("external_reference")
    if not eid_s: return jsonify({"ok":True}),200
    eid = int(eid_s)
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""INSERT INTO pagamentos (empresa_id,mp_payment_id,valor,status,pago_em)
                         VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                      (eid, str(payment_id), PRECO_MENSAL, status,
                       datetime.datetime.now() if status=="approved" else None))
            c.execute("UPDATE pagamentos SET status=%s,pago_em=%s WHERE mp_payment_id=%s",
                      (status, datetime.datetime.now() if status=="approved" else None, str(payment_id)))
            if status == "approved":
                c.execute("UPDATE empresas SET plano='ativo',plano_valido_ate=NOW()+INTERVAL '30 days' WHERE id=%s",(eid,))
    return jsonify({"ok":True}),200

# ─────────────────────────────────────────────────────────────
# PAINEL / DASHBOARD
# ─────────────────────────────────────────────────────────────
@app.route("/painel")
@login_required
def painel():
    eid    = session["empresa_id"]
    status = get_empresa_status(eid)
    trial_min = int(status.split(":")[1]) if status.startswith("trial:") else None
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as n FROM clientes WHERE empresa_id=%s",(eid,)); n_cli=c.fetchone()["n"]
            c.execute("SELECT COUNT(*) as n FROM os WHERE empresa_id=%s AND status NOT IN ('Entregue','Cancelado')",(eid,)); n_os=c.fetchone()["n"]
            c.execute("SELECT COUNT(*) as n FROM encomendas WHERE empresa_id=%s AND status != 'entregue'",(eid,)); n_enc=c.fetchone()["n"]
            c.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE empresa_id=%s",(eid,)); receita_vendas=c.fetchone()["t"]
            c.execute("SELECT COALESCE(SUM(valor),0) as t FROM financeiro WHERE empresa_id=%s AND tipo='Entrada'",(eid,)); receita_fin=c.fetchone()["t"]
            c.execute("SELECT * FROM estoque WHERE empresa_id=%s",(eid,)); est=c.fetchall()
            c.execute("SELECT * FROM acessorios WHERE empresa_id=%s AND qtd <= qtd_min",(eid,)); acess_crit=c.fetchall()
            c.execute("SELECT o.*,cl.nome as cli_nome FROM os o LEFT JOIN clientes cl ON o.cliente_id=cl.id WHERE o.empresa_id=%s ORDER BY o.id DESC LIMIT 8",(eid,)); ultimas_os=c.fetchall()
            c.execute("""SELECT TO_CHAR(data,'Mon/YY') as mes, COALESCE(SUM(valor),0) as total
                FROM financeiro WHERE empresa_id=%s AND tipo='Entrada' AND data>=CURRENT_DATE-INTERVAL '6 months'
                GROUP BY TO_CHAR(data,'Mon/YY'),EXTRACT(YEAR FROM data),EXTRACT(MONTH FROM data)
                ORDER BY EXTRACT(YEAR FROM data),EXTRACT(MONTH FROM data)""",(eid,)); receita_mensal=c.fetchall()
    n_crit = sum(1 for e in est if stock_status(e["qtd"],e["qtd_min"]) in ("Crítico","Sem Estoque"))
    est_crit = [e for e in est if stock_status(e["qtd"],e["qtd_min"]) in ("Crítico","Sem Estoque")]
    return render_template("painel.html",
        n_cli=n_cli, n_os=n_os, n_enc=n_enc,
        receita=fmtR(float(receita_vendas)+float(receita_fin)),
        n_crit=n_crit+len(acess_crit), est_crit=est_crit, acess_crit=acess_crit,
        ultimas_os=ultimas_os, receita_mensal=receita_mensal,
        stock_status=stock_status, fmtR=fmtR,
        trial_min=trial_min, plano_status=status)

# ─────────────────────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    eid = session["empresa_id"]
    q   = request.args.get("q","")
    with get_conn() as conn:
        with conn.cursor() as c:
            if q:
                c.execute("SELECT * FROM clientes WHERE empresa_id=%s AND (LOWER(nome) LIKE %s OR telefone LIKE %s) ORDER BY nome",
                          (eid,f"%{q.lower()}%",f"%{q}%"))
            else:
                c.execute("SELECT * FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            rows = c.fetchall()
    return render_template("clientes.html", clientes=rows, q=q)

@app.route("/clientes/novo", methods=["GET","POST"])
@login_required
def cliente_novo():
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""INSERT INTO clientes
                    (empresa_id,nome,telefone,whatsapp,email,cpfcnpj,tipo,endereco,cidade,uf,obs)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (session["empresa_id"],f["nome"],f.get("telefone"),f.get("whatsapp"),
                     f.get("email"),f.get("cpfcnpj"),f.get("tipo"),f.get("endereco"),
                     f.get("cidade"),f.get("uf"),f.get("obs")))
        flash("Cliente cadastrado! ✔","success")
        return redirect(url_for("clientes"))
    return render_template("form_cliente.html", cliente=None, titulo="Novo Cliente")

@app.route("/clientes/editar/<int:cid>", methods=["GET","POST"])
@login_required
def cliente_editar(cid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM clientes WHERE id=%s AND empresa_id=%s",(cid,eid))
            cli = c.fetchone()
    if not cli: return redirect(url_for("clientes"))
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""UPDATE clientes SET nome=%s,telefone=%s,whatsapp=%s,email=%s,
                    cpfcnpj=%s,tipo=%s,endereco=%s,cidade=%s,uf=%s,obs=%s
                    WHERE id=%s AND empresa_id=%s""",
                    (f["nome"],f.get("telefone"),f.get("whatsapp"),f.get("email"),
                     f.get("cpfcnpj"),f.get("tipo"),f.get("endereco"),f.get("cidade"),
                     f.get("uf"),f.get("obs"),cid,eid))
        flash("Cliente atualizado! ✔","success")
        return redirect(url_for("clientes"))
    return render_template("form_cliente.html", cliente=cli, titulo="Editar Cliente")

@app.route("/clientes/excluir/<int:cid>", methods=["POST"])
@login_required
def cliente_excluir(cid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM clientes WHERE id=%s AND empresa_id=%s",(cid,session["empresa_id"]))
    flash("Cliente excluído.","info")
    return redirect(url_for("clientes"))

# ─────────────────────────────────────────────────────────────
# CATEGORIAS DE PRODUTO
# ─────────────────────────────────────────────────────────────
@app.route("/categorias")
@login_required
def categorias():
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM categorias_produto WHERE empresa_id=%s ORDER BY nome",(eid,))
            rows = c.fetchall()
    return render_template("categorias.html", categorias=rows)

@app.route("/categorias/nova", methods=["POST"])
@login_required
def categoria_nova():
    nome = request.form.get("nome","").strip()
    tipo = request.form.get("tipo","produto")
    if nome:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("INSERT INTO categorias_produto (empresa_id,nome,tipo) VALUES (%s,%s,%s)",
                          (session["empresa_id"],nome,tipo))
        flash("Categoria criada! ✔","success")
    return redirect(url_for("categorias"))

@app.route("/categorias/excluir/<int:cid>", methods=["POST"])
@login_required
def categoria_excluir(cid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM categorias_produto WHERE id=%s AND empresa_id=%s",(cid,session["empresa_id"]))
    flash("Categoria excluída.","info")
    return redirect(url_for("categorias"))

# ─────────────────────────────────────────────────────────────
# PRODUTOS / ESTOQUE
# ─────────────────────────────────────────────────────────────
@app.route("/estoque")
@login_required
def estoque():
    eid = session["empresa_id"]
    q   = request.args.get("q","")
    cat = request.args.get("cat","")
    with get_conn() as conn:
        with conn.cursor() as c:
            sql = "SELECT * FROM estoque WHERE empresa_id=%s"
            params = [eid]
            if q:
                sql += " AND LOWER(descricao) LIKE %s"
                params.append(f"%{q.lower()}%")
            if cat:
                sql += " AND categoria=%s"
                params.append(cat)
            sql += " ORDER BY descricao"
            c.execute(sql, params)
            rows = c.fetchall()
            c.execute("SELECT DISTINCT categoria FROM estoque WHERE empresa_id=%s AND categoria IS NOT NULL ORDER BY categoria",(eid,))
            cats = [r["categoria"] for r in c.fetchall()]
    return render_template("estoque.html", pecas=rows, q=q, cat=cat, cats=cats,
                           stock_status=stock_status, fmtR=fmtR)

@app.route("/estoque/novo", methods=["GET","POST"])
@login_required
def estoque_novo():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""INSERT INTO estoque
                    (empresa_id,codigo,descricao,categoria,localizacao,fornecedor,qtd,qtd_min,custo,preco_venda,obs)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (eid,f.get("codigo"),f["descricao"],f.get("categoria"),
                     f.get("localizacao"),f.get("fornecedor"),
                     float(f.get("qtd") or 0),float(f.get("qtd_min") or 0),
                     float(f.get("custo") or 0),float(f.get("preco_venda") or 0),f.get("obs")))
        flash("Item cadastrado! ✔","success")
        return redirect(url_for("estoque"))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM categorias_produto WHERE empresa_id=%s ORDER BY nome",(eid,))
            cats = c.fetchall()
    # Categorias padrão para celular/info
    cats_padrao = ["Peças","Placas","Sub-placas","Acessórios","Celulares","Informática","Serviços","Outros"]
    return render_template("form_estoque.html", peca=None, titulo="Novo Item", cats=cats, cats_padrao=cats_padrao)

@app.route("/estoque/editar/<int:pid>", methods=["GET","POST"])
@login_required
def estoque_editar(pid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM estoque WHERE id=%s AND empresa_id=%s",(pid,eid))
            peca = c.fetchone()
    if not peca: return redirect(url_for("estoque"))
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""UPDATE estoque SET codigo=%s,descricao=%s,categoria=%s,localizacao=%s,
                    fornecedor=%s,qtd=%s,qtd_min=%s,custo=%s,preco_venda=%s,obs=%s,atualizado=CURRENT_DATE
                    WHERE id=%s AND empresa_id=%s""",
                    (f.get("codigo"),f["descricao"],f.get("categoria"),f.get("localizacao"),
                     f.get("fornecedor"),float(f.get("qtd") or 0),float(f.get("qtd_min") or 0),
                     float(f.get("custo") or 0),float(f.get("preco_venda") or 0),f.get("obs"),pid,eid))
        flash("Item atualizado! ✔","success")
        return redirect(url_for("estoque"))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM categorias_produto WHERE empresa_id=%s ORDER BY nome",(eid,))
            cats = c.fetchall()
    cats_padrao = ["Peças","Placas","Sub-placas","Acessórios","Celulares","Informática","Serviços","Outros"]
    return render_template("form_estoque.html", peca=peca, titulo="Editar Item", cats=cats, cats_padrao=cats_padrao)

@app.route("/estoque/excluir/<int:pid>", methods=["POST"])
@login_required
def estoque_excluir(pid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM estoque WHERE id=%s AND empresa_id=%s",(pid,session["empresa_id"]))
    flash("Item excluído.","info")
    return redirect(url_for("estoque"))

@app.route("/estoque/entrada/<int:pid>", methods=["POST"])
@login_required
def estoque_entrada(pid):
    eid = session["empresa_id"]
    qtd = float(request.form.get("qtd",0))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE estoque SET qtd=qtd+%s,atualizado=CURRENT_DATE WHERE id=%s AND empresa_id=%s",(qtd,pid,eid))
    flash(f"+{qtd} unidades adicionadas ao estoque! ✔","success")
    return redirect(url_for("estoque"))

# ─────────────────────────────────────────────────────────────
# ACESSÓRIOS (Películas, Capinhas, etc.)
# ─────────────────────────────────────────────────────────────
TIPOS_PELICULA = ["3D","5D","9D","Gel","Cerâmica","Privativa","Fosca","Espelhada","Comum"]
TIPOS_CAPINHA  = ["Silicone","Anti-impacto","Couro","Clear","Carteira","Magnética","Emborrachada"]
MARCAS_APARELHO = [
    "Samsung","iPhone (Apple)","Motorola","Xiaomi","POCO","Realme","Redmi",
    "LG","Nokia","Asus","Sony","Huawei","Honor","Infinix","Tecno","Multilaser",
    "Positivo","TCL","OnePlus","ZTE","Outra"
]
TIPOS_ACESSORIO = ["Película","Capinha","Carregador","Cabo","Fone","Película + Capinha","Suporte","Capa Emborrachada","Película Câmera","Outro"]

@app.route("/acessorios")
@login_required
def acessorios():
    eid  = session["empresa_id"]
    q    = request.args.get("q","")
    tipo = request.args.get("tipo","")
    marca= request.args.get("marca","")
    with get_conn() as conn:
        with conn.cursor() as c:
            sql = "SELECT * FROM acessorios WHERE empresa_id=%s"
            params = [eid]
            if q:
                sql += " AND (LOWER(descricao) LIKE %s OR LOWER(modelo_aparelho) LIKE %s OR LOWER(marca_aparelho) LIKE %s)"
                params += [f"%{q.lower()}%"]*3
            if tipo:
                sql += " AND tipo=%s"
                params.append(tipo)
            if marca:
                sql += " AND marca_aparelho=%s"
                params.append(marca)
            sql += " ORDER BY marca_aparelho,modelo_aparelho,tipo"
            c.execute(sql, params)
            rows = c.fetchall()
    return render_template("acessorios.html",
        acessorios=rows, q=q, tipo_filtro=tipo, marca_filtro=marca,
        tipos=TIPOS_ACESSORIO, marcas=MARCAS_APARELHO,
        stock_status=stock_status, fmtR=fmtR)

@app.route("/acessorios/novo", methods=["GET","POST"])
@login_required
def acessorio_novo():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""INSERT INTO acessorios
                    (empresa_id,tipo,subtipo,marca_aparelho,modelo_aparelho,descricao,
                     codigo,custo,preco_venda,qtd,qtd_min,fornecedor,cor,obs)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (eid,f["tipo"],f.get("subtipo"),f.get("marca_aparelho"),f.get("modelo_aparelho"),
                     f.get("descricao"),f.get("codigo"),
                     float(f.get("custo") or 0),float(f.get("preco_venda") or 0),
                     float(f.get("qtd") or 0),float(f.get("qtd_min") or 1),
                     f.get("fornecedor"),f.get("cor"),f.get("obs")))
        flash("Acessório cadastrado! ✔","success")
        return redirect(url_for("acessorios"))
    return render_template("form_acessorio.html", item=None, titulo="Novo Acessório",
        tipos=TIPOS_ACESSORIO, subtipos_pelicula=TIPOS_PELICULA,
        subtipos_capinha=TIPOS_CAPINHA, marcas=MARCAS_APARELHO)

@app.route("/acessorios/editar/<int:aid>", methods=["GET","POST"])
@login_required
def acessorio_editar(aid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM acessorios WHERE id=%s AND empresa_id=%s",(aid,eid))
            item = c.fetchone()
    if not item: return redirect(url_for("acessorios"))
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""UPDATE acessorios SET tipo=%s,subtipo=%s,marca_aparelho=%s,
                    modelo_aparelho=%s,descricao=%s,codigo=%s,custo=%s,preco_venda=%s,
                    qtd=%s,qtd_min=%s,fornecedor=%s,cor=%s,obs=%s
                    WHERE id=%s AND empresa_id=%s""",
                    (f["tipo"],f.get("subtipo"),f.get("marca_aparelho"),f.get("modelo_aparelho"),
                     f.get("descricao"),f.get("codigo"),
                     float(f.get("custo") or 0),float(f.get("preco_venda") or 0),
                     float(f.get("qtd") or 0),float(f.get("qtd_min") or 1),
                     f.get("fornecedor"),f.get("cor"),f.get("obs"),aid,eid))
        flash("Acessório atualizado! ✔","success")
        return redirect(url_for("acessorios"))
    return render_template("form_acessorio.html", item=item, titulo="Editar Acessório",
        tipos=TIPOS_ACESSORIO, subtipos_pelicula=TIPOS_PELICULA,
        subtipos_capinha=TIPOS_CAPINHA, marcas=MARCAS_APARELHO)

@app.route("/acessorios/excluir/<int:aid>", methods=["POST"])
@login_required
def acessorio_excluir(aid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM acessorios WHERE id=%s AND empresa_id=%s",(aid,session["empresa_id"]))
    flash("Acessório excluído.","info")
    return redirect(url_for("acessorios"))

@app.route("/acessorios/entrada/<int:aid>", methods=["POST"])
@login_required
def acessorio_entrada(aid):
    eid = session["empresa_id"]
    qtd = float(request.form.get("qtd",0))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE acessorios SET qtd=qtd+%s WHERE id=%s AND empresa_id=%s",(qtd,aid,eid))
    flash(f"+{int(qtd)} unidades adicionadas! ✔","success")
    return redirect(url_for("acessorios"))

# ─────────────────────────────────────────────────────────────
# ORDENS DE SERVIÇO
# ─────────────────────────────────────────────────────────────
@app.route("/os")
@login_required
def os_lista():
    eid    = session["empresa_id"]
    q      = request.args.get("q","")
    status = request.args.get("status","")
    with get_conn() as conn:
        with conn.cursor() as c:
            sql = """SELECT o.*,cl.nome as cli_nome FROM os o
                     LEFT JOIN clientes cl ON o.cliente_id=cl.id
                     WHERE o.empresa_id=%s"""
            params = [eid]
            if q:
                sql += " AND (LOWER(o.aparelho) LIKE %s OR LOWER(cl.nome) LIKE %s OR o.numero LIKE %s)"
                params += [f"%{q.lower()}%",f"%{q.lower()}%",f"%{q}%"]
            if status:
                sql += " AND o.status=%s"
                params.append(status)
            sql += " ORDER BY o.id DESC"
            c.execute(sql, params)
            rows = c.fetchall()
    return render_template("os_lista.html", os_lista=rows, q=q, status_filtro=status, fmtR=fmtR)

@app.route("/os/nova", methods=["GET","POST"])
@login_required
def os_nova():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        num = next_os_num(eid)
        cli_id = f.get("cliente_id") or None
        with get_conn() as conn:
            with conn.cursor() as c:
                # Busca nome do cliente
                nome_cli = f.get("cliente","")
                if cli_id:
                    c.execute("SELECT nome FROM clientes WHERE id=%s",(cli_id,))
                    r = c.fetchone()
                    if r: nome_cli = r["nome"]
                c.execute("""INSERT INTO os
                    (empresa_id,numero,data_abert,cliente_id,cliente,aparelho,imei,defeito,
                     senha_apar,acessorios,tecnico,status,pagto,data_prazo,obs)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (eid,num,f.get("data_abert") or datetime.date.today(),
                     cli_id,nome_cli,f.get("aparelho"),f.get("imei"),f.get("defeito"),
                     f.get("senha_apar"),f.get("acessorios"),f.get("tecnico"),
                     f.get("status","Aguardando"),f.get("pagto"),
                     f.get("data_prazo") or None,f.get("obs")))
                os_id = c.fetchone()["id"]
        flash(f"OS #{num} criada! ✔","success")
        return redirect(url_for("os_itens", oid=os_id))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,nome FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            clientes = c.fetchall()
    return render_template("form_os.html", os=None, titulo="Nova OS", clientes=clientes,
                           hoje=datetime.date.today().isoformat())

@app.route("/os/editar/<int:oid>", methods=["GET","POST"])
@login_required
def os_editar(oid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM os WHERE id=%s AND empresa_id=%s",(oid,eid))
            os_obj = c.fetchone()
    if not os_obj: return redirect(url_for("os_lista"))
    if request.method == "POST":
        f = request.form
        cli_id = f.get("cliente_id") or None
        with get_conn() as conn:
            with conn.cursor() as c:
                nome_cli = f.get("cliente","")
                if cli_id:
                    c.execute("SELECT nome FROM clientes WHERE id=%s",(cli_id,))
                    r = c.fetchone()
                    if r: nome_cli = r["nome"]
                c.execute("""UPDATE os SET data_abert=%s,cliente_id=%s,cliente=%s,aparelho=%s,
                    imei=%s,defeito=%s,senha_apar=%s,acessorios=%s,tecnico=%s,laudo=%s,
                    status=%s,desconto=%s,pagto=%s,pago=%s,data_prazo=%s,obs=%s
                    WHERE id=%s AND empresa_id=%s""",
                    (f.get("data_abert"),cli_id,nome_cli,f.get("aparelho"),f.get("imei"),
                     f.get("defeito"),f.get("senha_apar"),f.get("acessorios"),f.get("tecnico"),
                     f.get("laudo"),f.get("status"),float(f.get("desconto") or 0),
                     f.get("pagto"),f.get("pago"),f.get("data_prazo") or None,
                     f.get("obs"),oid,eid))
        flash("OS atualizada! ✔","success")
        return redirect(url_for("os_itens",oid=oid))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,nome FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            clientes = c.fetchall()
    return render_template("form_os.html", os=os_obj, titulo="Editar OS",
                           clientes=clientes, hoje=datetime.date.today().isoformat())

@app.route("/os/itens/<int:oid>")
@login_required
def os_itens(oid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM os WHERE id=%s AND empresa_id=%s",(oid,eid))
            os_obj = c.fetchone()
            c.execute("SELECT * FROM os_itens WHERE os_id=%s AND empresa_id=%s",(oid,eid))
            itens = c.fetchall()
            c.execute("SELECT * FROM estoque WHERE empresa_id=%s AND qtd>0 ORDER BY descricao",(eid,))
            estoque_disp = c.fetchall()
    return render_template("os_itens.html", os=os_obj, itens=itens,
                           estoque=estoque_disp, fmtR=fmtR)

@app.route("/os/itens/<int:oid>/add", methods=["POST"])
@login_required
def os_item_add(oid):
    eid = session["empresa_id"]
    f   = request.form
    estoque_id = f.get("estoque_id") or None
    descricao  = f.get("descricao","").strip()
    qtd        = float(f.get("qtd",1))
    valor_unit = float(f.get("valor_unit") or 0)
    subtotal   = qtd * valor_unit
    with get_conn() as conn:
        with conn.cursor() as c:
            if estoque_id:
                c.execute("SELECT * FROM estoque WHERE id=%s AND empresa_id=%s",(estoque_id,eid))
                p = c.fetchone()
                if p:
                    if not descricao: descricao = p["descricao"]
                    if not valor_unit:
                        valor_unit = float(p["preco_venda"] or p["custo"])
                        subtotal   = qtd * valor_unit
                    if float(p["qtd"]) < qtd:
                        flash("Quantidade insuficiente no estoque!","danger")
                        return redirect(url_for("os_itens",oid=oid))
                    c.execute("UPDATE estoque SET qtd=qtd-%s,atualizado=CURRENT_DATE WHERE id=%s AND empresa_id=%s",
                              (qtd,estoque_id,eid))
            c.execute("""INSERT INTO os_itens
                (empresa_id,os_id,estoque_id,descricao,qtd,valor_unit,subtotal)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (eid,oid,estoque_id,descricao,qtd,valor_unit,subtotal))
            c.execute("UPDATE os SET total=total+%s WHERE id=%s AND empresa_id=%s",(subtotal,oid,eid))
    flash("Item adicionado! ✔","success")
    return redirect(url_for("os_itens",oid=oid))

@app.route("/os/itens/remover/<int:item_id>/<int:oid>", methods=["POST"])
@login_required
def os_item_remover(item_id, oid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM os_itens WHERE id=%s",(item_id,))
            item = c.fetchone()
            if item:
                if item["estoque_id"]:
                    c.execute("UPDATE estoque SET qtd=qtd+%s,atualizado=CURRENT_DATE WHERE id=%s AND empresa_id=%s",
                              (item["qtd"],item["estoque_id"],eid))
                c.execute("UPDATE os SET total=total-%s WHERE id=%s AND empresa_id=%s",(item["subtotal"],oid,eid))
                c.execute("DELETE FROM os_itens WHERE id=%s",(item_id,))
    flash("Item removido.","info")
    return redirect(url_for("os_itens",oid=oid))

@app.route("/os/excluir/<int:oid>", methods=["POST"])
@login_required
def os_excluir(oid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM os WHERE id=%s AND empresa_id=%s",(oid,session["empresa_id"]))
    flash("OS excluída.","info")
    return redirect(url_for("os_lista"))

# Impressão de OS — Térmica 80mm / 50mm
@app.route("/os/imprimir/<int:oid>")
@login_required
def os_imprimir(oid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM os WHERE id=%s AND empresa_id=%s",(oid,eid))
            os_obj = c.fetchone()
            c.execute("SELECT * FROM os_itens WHERE os_id=%s",(oid,))
            itens  = c.fetchall()
            c.execute("SELECT * FROM empresas WHERE id=%s",(eid,))
            empresa = c.fetchone()
    largura = request.args.get("l", empresa.get("impressora","80mm"))
    return render_template("imprimir_os.html", os=os_obj, itens=itens,
                           empresa=empresa, largura=largura, fmtR=fmtR)

# ─────────────────────────────────────────────────────────────
# ENCOMENDAS
# ─────────────────────────────────────────────────────────────
@app.route("/encomendas")
@login_required
def encomendas():
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""SELECT e.*,cl.nome as cli_nome FROM encomendas e
                LEFT JOIN clientes cl ON e.cliente_id=cl.id
                WHERE e.empresa_id=%s ORDER BY e.id DESC""",(eid,))
            rows = c.fetchall()
    return render_template("encomendas.html", encomendas=rows, fmtR=fmtR)

@app.route("/encomendas/nova", methods=["GET","POST"])
@login_required
def encomenda_nova():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        cli_id  = f.get("cliente_id") or None
        total   = float(f.get("total") or 0)
        entrada = float(f.get("entrada") or 0)
        with get_conn() as conn:
            with conn.cursor() as c:
                nome_cli = f.get("cliente","")
                if cli_id:
                    c.execute("SELECT nome FROM clientes WHERE id=%s",(cli_id,))
                    r = c.fetchone()
                    if r: nome_cli = r["nome"]
                c.execute("""INSERT INTO encomendas
                    (empresa_id,cliente_id,cliente,produto,total,entrada,fpgto_entrada,
                     fpgto_saldo,data_prazo,status,obs)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (eid,cli_id,nome_cli,f["produto"],total,entrada,
                     f.get("fpgto_entrada"),f.get("fpgto_saldo","A definir"),
                     f.get("data_prazo") or None,f.get("status","aguardando"),f.get("obs")))
                if entrada > 0:
                    c.execute("""INSERT INTO financeiro (empresa_id,tipo,categoria,descricao,valor,pagto,pago)
                        VALUES (%s,'Entrada','Encomendas',%s,%s,%s,'Sim')""",
                        (eid,f"Entrada encomenda: {f['produto']}",entrada,f.get("fpgto_entrada")))
        flash("Encomenda cadastrada! ✔","success")
        return redirect(url_for("encomendas"))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,nome FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            clientes = c.fetchall()
    return render_template("form_encomenda.html", enc=None, titulo="Nova Encomenda",
                           clientes=clientes, hoje=datetime.date.today().isoformat())

@app.route("/encomendas/editar/<int:eid_enc>", methods=["GET","POST"])
@login_required
def encomenda_editar(eid_enc):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM encomendas WHERE id=%s AND empresa_id=%s",(eid_enc,eid))
            enc = c.fetchone()
    if not enc: return redirect(url_for("encomendas"))
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""UPDATE encomendas SET produto=%s,total=%s,entrada=%s,
                    fpgto_entrada=%s,fpgto_saldo=%s,data_prazo=%s,status=%s,obs=%s
                    WHERE id=%s AND empresa_id=%s""",
                    (f["produto"],float(f.get("total") or 0),float(f.get("entrada") or 0),
                     f.get("fpgto_entrada"),f.get("fpgto_saldo"),
                     f.get("data_prazo") or None,f.get("status"),f.get("obs"),eid_enc,eid))
        flash("Encomenda atualizada! ✔","success")
        return redirect(url_for("encomendas"))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,nome FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            clientes = c.fetchall()
    return render_template("form_encomenda.html", enc=enc, titulo="Editar Encomenda",
                           clientes=clientes, hoje=datetime.date.today().isoformat())

@app.route("/encomendas/excluir/<int:eid_enc>", methods=["POST"])
@login_required
def encomenda_excluir(eid_enc):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM encomendas WHERE id=%s AND empresa_id=%s",(eid_enc,session["empresa_id"]))
    flash("Encomenda excluída.","info")
    return redirect(url_for("encomendas"))

# ─────────────────────────────────────────────────────────────
# PDV / VENDAS
# ─────────────────────────────────────────────────────────────
@app.route("/vendas")
@login_required
def vendas():
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""SELECT v.*,cl.nome as cli_nome FROM vendas v
                LEFT JOIN clientes cl ON v.cliente_id=cl.id
                WHERE v.empresa_id=%s ORDER BY v.id DESC LIMIT 100""",(eid,))
            rows = c.fetchall()
    return render_template("vendas.html", vendas=rows, fmtR=fmtR)

@app.route("/pdv", methods=["GET","POST"])
@login_required
def pdv():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        cli_id  = f.get("cliente_id") or None
        total   = float(f.get("total") or 0)
        desconto= float(f.get("desconto") or 0)
        pagto   = f.get("pagto","Dinheiro")
        parcelas= int(f.get("parcelas") or 1)
        itens_json = f.get("itens_json","[]")
        try: itens = json.loads(itens_json)
        except: itens = []
        with get_conn() as conn:
            with conn.cursor() as c:
                nome_cli = ""
                if cli_id:
                    c.execute("SELECT nome FROM clientes WHERE id=%s",(cli_id,))
                    r = c.fetchone()
                    if r: nome_cli = r["nome"]
                c.execute("""INSERT INTO vendas
                    (empresa_id,cliente_id,cliente,total,desconto,pagto,parcelas,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'finalizada') RETURNING id""",
                    (eid,cli_id,nome_cli,total,desconto,pagto,parcelas))
                venda_id = c.fetchone()["id"]
                for item in itens:
                    subtotal = float(item.get("qtd",1))*float(item.get("preco",0))
                    est_id   = item.get("estoque_id") or None
                    acess_id = item.get("acessorio_id") or None
                    c.execute("""INSERT INTO venda_itens
                        (empresa_id,venda_id,estoque_id,acessorio_id,descricao,qtd,valor_unit,subtotal)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (eid,venda_id,est_id,acess_id,item.get("descricao",""),
                         float(item.get("qtd",1)),float(item.get("preco",0)),subtotal))
                    if est_id:
                        c.execute("UPDATE estoque SET qtd=qtd-%s,atualizado=CURRENT_DATE WHERE id=%s AND empresa_id=%s",
                                  (item.get("qtd",1),est_id,eid))
                    if acess_id:
                        c.execute("UPDATE acessorios SET qtd=qtd-%s WHERE id=%s AND empresa_id=%s",
                                  (item.get("qtd",1),acess_id,eid))
                c.execute("""INSERT INTO financeiro (empresa_id,tipo,categoria,descricao,valor,pagto,pago)
                    VALUES (%s,'Entrada','Vendas',%s,%s,%s,'Sim')""",
                    (eid,f"Venda #{venda_id} — {pagto}",total-desconto,pagto))
        return jsonify({"ok":True,"venda_id":venda_id})
    # GET — carrega dados para PDV
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id,nome FROM clientes WHERE empresa_id=%s ORDER BY nome",(eid,))
            clientes = c.fetchall()
            c.execute("SELECT * FROM estoque WHERE empresa_id=%s AND qtd>0 ORDER BY descricao",(eid,))
            estoque  = c.fetchall()
            c.execute("SELECT * FROM acessorios WHERE empresa_id=%s AND qtd>0 ORDER BY marca_aparelho,modelo_aparelho,tipo",(eid,))
            acessorios = c.fetchall()
    return render_template("pdv.html", clientes=clientes, estoque=estoque,
                           acessorios=acessorios, fmtR=fmtR)

@app.route("/vendas/cupom/<int:vid>")
@login_required
def venda_cupom(vid):
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM vendas WHERE id=%s AND empresa_id=%s",(vid,eid))
            venda = c.fetchone()
            c.execute("SELECT * FROM venda_itens WHERE venda_id=%s",(vid,))
            itens = c.fetchall()
            c.execute("SELECT * FROM empresas WHERE id=%s",(eid,))
            empresa = c.fetchone()
    largura = request.args.get("l", empresa.get("impressora","80mm"))
    return render_template("cupom_venda.html", venda=venda, itens=itens,
                           empresa=empresa, largura=largura, fmtR=fmtR)

# ─────────────────────────────────────────────────────────────
# FINANCEIRO
# ─────────────────────────────────────────────────────────────
@app.route("/financeiro")
@login_required
def financeiro():
    eid  = session["empresa_id"]
    tipo = request.args.get("tipo","")
    with get_conn() as conn:
        with conn.cursor() as c:
            sql = "SELECT * FROM financeiro WHERE empresa_id=%s"
            params = [eid]
            if tipo:
                sql += " AND tipo=%s"
                params.append(tipo)
            sql += " ORDER BY data DESC,id DESC LIMIT 200"
            c.execute(sql, params)
            rows = c.fetchall()
            c.execute("SELECT COALESCE(SUM(valor),0) as t FROM financeiro WHERE empresa_id=%s AND tipo='Entrada'",(eid,)); rec=c.fetchone()["t"]
            c.execute("SELECT COALESCE(SUM(valor),0) as t FROM financeiro WHERE empresa_id=%s AND tipo='Saída'",(eid,)); sai=c.fetchone()["t"]
    return render_template("financeiro.html", lancamentos=rows, fmtR=fmtR,
                           receita=fmtR(rec), saida=fmtR(sai),
                           saldo=fmtR(float(rec)-float(sai)), tipo_filtro=tipo)

@app.route("/financeiro/novo", methods=["POST"])
@login_required
def financeiro_novo():
    eid = session["empresa_id"]
    f   = request.form
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""INSERT INTO financeiro (empresa_id,data,tipo,categoria,descricao,valor,pagto,pago,obs)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (eid, f.get("data") or datetime.date.today(),
                 f["tipo"],f.get("categoria"),f["descricao"],
                 float(f.get("valor") or 0),f.get("pagto"),f.get("pago","Sim"),f.get("obs")))
    flash("Lançamento registrado! ✔","success")
    return redirect(url_for("financeiro"))

@app.route("/financeiro/excluir/<int:fid>", methods=["POST"])
@login_required
def financeiro_excluir(fid):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM financeiro WHERE id=%s AND empresa_id=%s",(fid,session["empresa_id"]))
    flash("Lançamento excluído.","info")
    return redirect(url_for("financeiro"))

# ─────────────────────────────────────────────────────────────
# RELATÓRIOS
# ─────────────────────────────────────────────────────────────
@app.route("/relatorios")
@login_required
def relatorios():
    eid = session["empresa_id"]
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""SELECT TO_CHAR(data,'Mon/YY') as mes, COALESCE(SUM(valor),0) as total
                FROM financeiro WHERE empresa_id=%s AND tipo='Entrada'
                AND data>=CURRENT_DATE-INTERVAL '6 months'
                GROUP BY TO_CHAR(data,'Mon/YY'),EXTRACT(YEAR FROM data),EXTRACT(MONTH FROM data)
                ORDER BY EXTRACT(YEAR FROM data),EXTRACT(MONTH FROM data)""",(eid,))
            receita_mensal = c.fetchall()
            c.execute("SELECT status,COUNT(*) as n FROM os WHERE empresa_id=%s GROUP BY status ORDER BY n DESC",(eid,))
            os_por_status = c.fetchall()
            c.execute("""SELECT descricao,SUM(qtd) as total_qtd,SUM(subtotal) as total_valor
                FROM os_itens WHERE empresa_id=%s
                GROUP BY descricao ORDER BY total_qtd DESC LIMIT 10""",(eid,))
            pecas_mais_usadas = c.fetchall()
            c.execute("""SELECT tipo,COUNT(*) as n,SUM(qtd) as total_qtd
                FROM acessorios WHERE empresa_id=%s GROUP BY tipo ORDER BY total_qtd DESC""",(eid,))
            acess_por_tipo = c.fetchall()
            c.execute("SELECT COALESCE(SUM(valor),0) as t FROM financeiro WHERE empresa_id=%s AND tipo='Entrada'",(eid,)); rec=c.fetchone()["t"]
            c.execute("SELECT COALESCE(SUM(valor),0) as t FROM financeiro WHERE empresa_id=%s AND tipo='Saída'",(eid,)); sai=c.fetchone()["t"]
            c.execute("SELECT COUNT(*) as n FROM os WHERE empresa_id=%s",(eid,)); total_os=c.fetchone()["n"]
            c.execute("SELECT COUNT(*) as n FROM clientes WHERE empresa_id=%s",(eid,)); total_cli=c.fetchone()["n"]
            c.execute("SELECT COALESCE(AVG(total),0) as t FROM os WHERE empresa_id=%s AND total>0",(eid,)); ticket=c.fetchone()["t"]
    return render_template("relatorios.html",
        receita_mensal=receita_mensal, os_por_status=os_por_status,
        pecas_mais_usadas=pecas_mais_usadas, acess_por_tipo=acess_por_tipo,
        rec_total=fmtR(rec), sai_total=fmtR(sai), saldo=fmtR(float(rec)-float(sai)),
        total_os=total_os, total_cli=total_cli, ticket=fmtR(ticket), fmtR=fmtR)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DA LOJA
# ─────────────────────────────────────────────────────────────
@app.route("/configuracoes", methods=["GET","POST"])
@login_required
def configuracoes():
    eid = session["empresa_id"]
    if request.method == "POST":
        f = request.form
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""UPDATE empresas SET loja_nome=%s,loja_cnpj=%s,loja_tel=%s,
                    loja_end=%s,loja_cidade=%s,loja_uf=%s,impressora=%s
                    WHERE id=%s""",
                    (f.get("loja_nome"),f.get("loja_cnpj"),f.get("loja_tel"),
                     f.get("loja_end"),f.get("loja_cidade"),f.get("loja_uf"),
                     f.get("impressora","80mm"),eid))
        session["empresa_nome"] = f.get("loja_nome") or session["empresa_nome"]
        flash("Configurações salvas! ✔","success")
        return redirect(url_for("configuracoes"))
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM empresas WHERE id=%s",(eid,))
            empresa = c.fetchone()
    return render_template("configuracoes.html", empresa=empresa)

# ─────────────────────────────────────────────────────────────
# API — Orange Tech Admin Hub
# ─────────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    if not api_auth(): return jsonify({"erro":"Nao autorizado"}),401
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) as n FROM empresas"); total=c.fetchone()["n"]
                c.execute("SELECT COUNT(*) as n FROM empresas WHERE plano='ativo' AND plano_valido_ate>NOW()"); ativas=c.fetchone()["n"]
                c.execute("SELECT COUNT(*) as n FROM empresas WHERE plano='trial' AND trial_inicio+INTERVAL '1 hour'>NOW()"); trial=c.fetchone()["n"]
                c.execute("SELECT COALESCE(SUM(valor),0) as t FROM pagamentos WHERE status='approved' AND EXTRACT(MONTH FROM criado_em)=EXTRACT(MONTH FROM NOW())"); receita_mes=c.fetchone()["t"]
                c.execute("SELECT COALESCE(SUM(valor),0) as t FROM pagamentos WHERE status='approved'"); receita_total=c.fetchone()["t"]
                c.execute("SELECT COUNT(*) as n FROM empresas WHERE EXTRACT(MONTH FROM criado_em)=EXTRACT(MONTH FROM NOW())"); novos_mes=c.fetchone()["n"]
                c.execute("""SELECT TO_CHAR(criado_em,'Mon') as mes,COALESCE(SUM(valor),0) as valor
                    FROM pagamentos WHERE status='approved'
                    GROUP BY TO_CHAR(criado_em,'Mon'),EXTRACT(MONTH FROM criado_em),EXTRACT(YEAR FROM criado_em)
                    ORDER BY EXTRACT(YEAR FROM criado_em),EXTRACT(MONTH FROM criado_em) DESC LIMIT 6""")
                historico = list(reversed(c.fetchall()))
        return jsonify({
            "total_empresas":total,"ativas":ativas,"trial":trial,
            "expiradas":max(0,total-ativas-trial),
            "receita_mes":float(receita_mes),"receita_total":float(receita_total),
            "novos_mes":novos_mes,
            "historico_receita":[{"mes":h["mes"],"valor":float(h["valor"])} for h in historico]
        })
    except Exception as e:
        return jsonify({"erro":str(e)}),500

@app.route("/api/empresas")
def api_empresas_hub():
    if not api_auth(): return jsonify({"erro":"Nao autorizado"}),401
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT id,nome,usuario,plano,plano_valido_ate,trial_inicio,criado_em FROM empresas ORDER BY criado_em DESC")
                rows = c.fetchall()
        return jsonify({"empresas":[{
            "id":e["id"],"nome":e["nome"],"usuario":e["usuario"],"plano":e["plano"],
            "plano_valido_ate":e["plano_valido_ate"].isoformat() if e["plano_valido_ate"] else None,
            "trial_inicio":e["trial_inicio"].isoformat() if e["trial_inicio"] else None,
            "criado_em":e["criado_em"].isoformat() if e["criado_em"] else None
        } for e in rows]})
    except Exception as e:
        return jsonify({"erro":str(e)}),500

@app.route("/api/admin/liberar/<int:emp_id>", methods=["POST"])
def api_admin_liberar(emp_id):
    if not api_auth(): return jsonify({"erro":"Nao autorizado"}),401
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE empresas SET plano='ativo',plano_valido_ate=NOW()+INTERVAL '30 days' WHERE id=%s",(emp_id,))
    return jsonify({"ok":True})

@app.route("/api/admin/trial/<int:emp_id>", methods=["POST"])
def api_admin_trial(emp_id):
    if not api_auth(): return jsonify({"erro":"Nao autorizado"}),401
    horas = float((request.json or {}).get("horas",1))
    segundos = int(horas*3600)
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""UPDATE empresas SET plano='trial',trial_inicio=NOW(),
                plano_valido_ate=NOW()+(INTERVAL '1 second'*%s) WHERE id=%s""",(segundos,emp_id))
    return jsonify({"ok":True,"horas":horas})

@app.route("/api/admin/bloquear/<int:emp_id>", methods=["POST"])
def api_admin_bloquear(emp_id):
    if not api_auth(): return jsonify({"erro":"Nao autorizado"}),401
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE empresas SET plano='expirado',plano_valido_ate=NOW() WHERE id=%s",(emp_id,))
    return jsonify({"ok":True})

# ─────────────────────────────────────────────────────────────
# INICIALIZAÇÃO
# ─────────────────────────────────────────────────────────────
try:
    init_db()
    print("✅ TechOS — Banco inicializado!")
except Exception as e:
    print(f"⚠️  init_db: {e}")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT",5000)))

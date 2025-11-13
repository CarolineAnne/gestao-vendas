import streamlit as st
import mysql.connector
import pandas as pd
import altair as alt
from datetime import date
from io import BytesIO
import hashlib
import locale

import os
import mysql.connector

# ==============================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================
st.set_page_config(page_title="Gestão de Vendas", layout="wide")

# Define idioma para datas (Windows e Linux)
import locale
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "")


# ==============================
# 🔗 CONEXÃO COM O BANCO
# ==============================
def conectar():
    return mysql.connector.connect(
        host=st.secrets["MYSQLHOST"],
        user=st.secrets["MYSQLUSER"],
        password=st.secrets["MYSQLPASSWORD"],
        database=st.secrets["MYSQLDATABASE"],
        port=st.secrets["MYSQLPORT"]
    )



# ==============================
# 🔒 SISTEMA DE LOGIN SEGURO
# ==============================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None


def hash_senha(senha):
    """Criptografa a senha com SHA-256."""
    return hashlib.sha256(senha.encode()).hexdigest()

try:
    con = conectar()
    st.success("✅ Conexão com o banco realizada com sucesso!")
    con.close()
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

def login_page():
    st.title("🔐 Login de Acesso")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        con = conectar()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario,))
        user_data = cur.fetchone()
        con.close()

        if user_data and user_data["senha"] == hash_senha(senha):
            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario
            st.success(f"Bem-vindo(a), {usuario}!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")


def logout():
    st.session_state["logado"] = False
    st.session_state["usuario"] = None
    st.rerun()

# ==============================
# 🏠 HOME
# ==============================
def home_page():
    st.title("📊 Resumo do Dia")
    hoje = date.today()

    con = conectar()
    sql = """
        SELECT COUNT(*) AS qt, SUM(v.quantidade * v.preco_unit) AS total
        FROM vendas v
        WHERE v.data = %s
    """
    df = pd.read_sql(sql, con, params=(hoje,))
    con.close()

    qt = df["qt"].iloc[0] or 0
    total = df["total"].iloc[0] or 0

    st.metric("Vendas do dia", qt)
    st.metric("Total vendido", f"R$ {total:,.2f}".replace(",", "."))

# ==============================
# 📦 PRODUTOS
# ==============================
def produtos_page():
    st.title("📦 Cadastro de Produtos")

    con = conectar()
    cur = con.cursor(dictionary=True)

    nome = st.text_input("Nome do produto")
    preco = st.number_input("Preço unitário", min_value=0.0, step=0.01, key="preco_add")

    if st.button("Salvar Produto"):
        cur.execute("SELECT id FROM produtos WHERE nome=%s", (nome,))
        if cur.fetchone():
            st.error("❌ Produto já cadastrado!")
        else:
            cur.execute("INSERT INTO produtos (nome, preco) VALUES (%s, %s)", (nome, preco))
            con.commit()
            st.success("✅ Produto cadastrado com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("Editar / Excluir Produtos")

    cur.execute("SELECT * FROM produtos")
    lista = cur.fetchall()
    con.close()

    if lista:
        produto_sel = st.selectbox("Selecione o produto", lista, format_func=lambda x: x["nome"])
        novo_nome = st.text_input("Novo nome", produto_sel["nome"])
        novo_preco = st.number_input("Novo preço", value=float(produto_sel["preco"]))

        c1, c2 = st.columns(2)
        if c1.button("Salvar Alteração"):
            con = conectar()
            cur = con.cursor()
            cur.execute("UPDATE produtos SET nome=%s, preco=%s WHERE id=%s",
                        (novo_nome, novo_preco, produto_sel["id"]))
            con.commit()
            con.close()
            st.success("✅ Alterado!")
            st.rerun()

        if c2.button("Excluir Produto"):
            con = conectar()
            cur = con.cursor()
            cur.execute("DELETE FROM produtos WHERE id=%s", (produto_sel["id"],))
            con.commit()
            con.close()
            st.warning("🚮 Produto excluído!")
            st.rerun()

# ==============================
# 💰 VENDAS
# ==============================
def vendas_page():
    st.title("💰 Registrar Venda")

    con = conectar()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM produtos")
    produtos = cur.fetchall()

    if not produtos:
        st.warning("Nenhum produto cadastrado!")
        return

    prod = st.selectbox("Produto", produtos, format_func=lambda x: x["nome"])
    qtd = st.number_input("Quantidade", min_value=1)
    data = st.date_input("Data", value=date.today())

    if st.button("Registrar Venda"):
        cur.execute("INSERT INTO vendas (data, produto_id, quantidade, preco_unit) VALUES (%s,%s,%s,%s)",
                    (data, prod["id"], qtd, prod["preco"]))
        con.commit()
        con.close()
        st.success("✅ Venda registrada com sucesso!")
        st.rerun()

# ==============================
# 📄 RELATÓRIOS
# ==============================
def relatorios_page():
    st.title("📄 Relatórios de Vendas")

    data_ini = st.date_input("Data inicial")
    data_fim = st.date_input("Data final")

    if st.button("Gerar Relatório"):
        con = conectar()
        sql = """
        SELECT v.data, p.nome, v.quantidade, v.preco_unit,
               (v.quantidade * v.preco_unit) AS total
        FROM vendas v
        JOIN produtos p ON p.id = v.produto_id
        WHERE v.data BETWEEN %s AND %s
        ORDER BY v.data
        """
        df = pd.read_sql(sql, con, params=(data_ini, data_fim))
        con.close()

        if df.empty:
            st.warning("Nenhum registro encontrado!")
            return

        df_totais = df.groupby("data")["total"].sum().reset_index()
        df_totais.columns = ["Data", "Total do Dia"]

        total_geral = df["total"].sum()

        st.dataframe(df)
        st.dataframe(df_totais)
        st.success(f"💰 Total Geral: R$ {total_geral:.2f}")

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Detalhado", index=False)
            df_totais.to_excel(writer, sheet_name="Totais por Dia", index=False)
        st.download_button(
            label="⬇ Baixar Excel",
            data=buffer.getvalue(),
            file_name="relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ==============================
# 📈 ESTATÍSTICAS
# ==============================
def estatisticas_page():
    st.title("📊 Total por Dia")

    con = conectar()
    sql = """
    SELECT data, SUM(v.quantidade * v.preco_unit) AS total
    FROM vendas v
    GROUP BY data
    ORDER BY data
    """
    df = pd.read_sql(sql, con)
    con.close()

    if df.empty:
        st.warning("Sem dados disponíveis.")
        return

    graf = alt.Chart(df).mark_line(point=True).encode(
        x="data:T",
        y="total:Q"
    )
    st.altair_chart(graf, use_container_width=True)

# ==============================
# 🚀 EXECUÇÃO
# ==============================
if not st.session_state["logado"]:
    login_page()
else:
    with st.sidebar:
        st.subheader(f"👤 Usuário: {st.session_state['usuario']}")
        menu = st.selectbox("Menu", ["Home", "Produtos", "Vendas", "Relatórios", "Estatísticas"])
        if st.button("🚪 Sair"):
            logout()

    if menu == "Home":
        home_page()
    elif menu == "Produtos":
        produtos_page()
    elif menu == "Vendas":
        vendas_page()
    elif menu == "Relatórios":
        relatorios_page()
    elif menu == "Estatísticas":
        estatisticas_page()









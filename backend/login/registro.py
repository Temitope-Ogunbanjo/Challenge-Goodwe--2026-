import re
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Configuração do Banco de Dados
# Para produção, troque a linha abaixo pelo URI do PostgreSQL/MySQL (ex: "postgresql://user:pass@localhost/db")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ev_charging.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================================
# MODELOS DO BANCO DE DADOS (ORM)
# ==========================================


class Usuario(db.Model):
    """Modelo da tabela de usuários.

    Campos únicos (email, CPF, telefone) garantem que não existam duplicatas no sistema.
    """

    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    telefone = db.Column(db.String(20), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    cep_endereco = db.Column(db.String(200), nullable=False)

    # Relacionamento 1-para-Muitos com Veículos
    veiculos = db.relationship(
        "Veiculo", backref="proprietario", lazy=True, cascade="all, delete-orphan"
    )


class Veiculo(db.Model):
    """Modelo da tabela de veículos associados ao usuário."""

    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo_ano = db.Column(db.String(80), nullable=False)
    placa = db.Column(db.String(10), unique=True, nullable=False)
    cor = db.Column(db.String(30), nullable=False)
    carroceria = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False
    )


# ==========================================
# FUNÇÕES DE VALIDAÇÃO REGRAS DE NEGÓCIO
# ==========================================


def validar_senha(senha):
    """Valida se a senha tem no mínimo 4 caracteres e pelo menos 2 letras."""
    if len(senha) < 4:
        return False
    letras = len(re.findall(r"[a-zA-Z]", senha))
    return letras >= 2


def sanitizar_numeros(texto):
    """Remove caracteres especiais de CPF e Telefone (deixa apenas números)."""
    return re.sub(r"\D", "", texto)


# ==========================================
# ROTAS DA API
# ==========================================


@app.route("/api/registro", methods=["POST"])
def registrar_usuario():
    """Rota para cadastro do usuário e veículo."""
    data = request.get_json()

    # 1. Validação de Senha
    senha = data.get("senha", "")
    if not validar_senha(senha):
        return (
            jsonify(
                {
                    "erro": "A senha deve ter no mínimo 4 caracteres e conter pelo menos 2 letras."
                }
            ),
            400,
        )

    # 2. Tratamento de identificadores únicos
    email = data.get("email", "").strip().lower()
    cpf = sanitizar_numeros(data.get("cpf", ""))
    telefone = sanitizar_numeros(data.get("telefone", ""))

    # 3. Verificação de Duplicidades (Email, CPF, Telefone)
    if Usuario.query.filter_by(email=email).first():
        return jsonify({"erro": "Este e-mail já está cadastrado."}), 409
    if Usuario.query.filter_by(cpf=cpf).first():
        return jsonify({"erro": "Este CPF já está cadastrado."}), 409
    if Usuario.query.filter_by(telefone=telefone).first():
        return jsonify({"erro": "Este telefone já está cadastrado."}), 409

    # 4. Criação do Usuário
    novo_usuario = Usuario(
        nome_completo=data.get("nome_completo"),
        email=email,
        cpf=cpf,
        telefone=telefone,
        senha_hash=generate_password_hash(senha),
        cep_endereco=data.get("cep_endereco"),
    )

    db.session.add(novo_usuario)
    db.session.flush()  # Gera o ID do novo usuário sem comitar a transação ainda

    # 5. Associação do Veículo
    veiculo_data = data.get("veiculo", {})
    novo_veiculo = Veiculo(
        marca=veiculo_data.get("marca"),
        modelo_ano=veiculo_data.get("modelo_ano"),
        placa=veiculo_data.get("placa", "").upper(),
        cor=veiculo_data.get("cor"),
        carroceria=veiculo_data.get("carroceria"),
        usuario_id=novo_usuario.id,
    )

    db.session.add(novo_veiculo)
    db.session.commit()

    return (
        jsonify(
            {
                "mensagem": "Usuário e veículo cadastrados com sucesso!",
                "usuario_id": novo_usuario.id,
            }
        ),
        201,
    )


@app.route("/api/login", methods=["POST"])
def login():
    """Passo 1 do Login: Valida credenciais e gera código de verificação (2FA)."""
    data = request.get_json()
    identificador = data.get("login")  # Pode ser Email ou CPF
    senha = data.get("senha")

    if not identificador or not senha:
        return (
            jsonify({"erro": "Forneça o login (Email/CPF) e a senha."}),
            400,
        )

    # Identifica se a entrada é CPF ou Email
    identificador_limpo = sanitizar_numeros(identificador)
    usuario = Usuario.query.filter(
        (Usuario.email == identificador.lower())
        | (Usuario.cpf == identificador_limpo)
    ).first()

    if not usuario or not check_password_hash(usuario.senha_hash, senha):
        return jsonify({"erro": "Credenciais inválidas."}), 401

    # SIMULAÇÃO DE ENVIO DE CÓDIGO 2FA (WhatsApp / SMS / Email)
    # Em produção, aqui você chamará APIs externas como Twilio ou SendGrid
    codigo_2fa = "123456"  # Exemplo fixo para testes dev

    return jsonify(
        {
            "mensagem": "Credenciais válidas. Digite o código enviado para o seu dispositivo.",
            "usuario_id": usuario.id,
            "metodo_envio": "WhatsApp/Email",
            "codigo_dev_teste": codigo_2fa,  # Remover em produção!
        }
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Cria as tabelas do banco automaticamente no SQLite local
    app.run(debug=True)
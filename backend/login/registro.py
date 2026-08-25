import re
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS (PostgreSQL / Render)
# ==========================================
DATABASE_URL = "postgresql+psycopg://goodwe_back:mBs0XKLEm2H8t34EovfH8Wwccm2sKUPP@dpg-da6elg8n74is73es5220-a.virginia-postgres.render.com/db_goodwe"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ==========================================
# MODELOS DO BANCO DE DADOS (ORM - SQLAlchemy)
# ==========================================


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    cpf = Column(String(14), unique=True, nullable=False, index=True)
    telefone = Column(String(20), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    cep_endereco = Column(String(200), nullable=False)

    veiculos = relationship(
        "VeiculoModel",
        back_populates="proprietario",
        cascade="all, delete-orphan",
    )


class VeiculoModel(Base):
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(50), nullable=False)
    modelo_ano = Column(String(80), nullable=False)
    placa = Column(String(10), unique=True, nullable=False, index=True)
    cor = Column(String(30), nullable=False)
    carroceria = Column(String(50), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    proprietario = relationship("UsuarioModel", back_populates="veiculos")


# Criação automática das tabelas no PostgreSQL
Base.metadata.create_all(bind=engine)

# ==========================================
# SCHEMAS DE VALIDAÇÃO (Pydantic)
# ==========================================


class VeiculoSchema(BaseModel):
    marca: str
    modelo_ano: str
    placa: str
    cor: str
    carroceria: str


class RegistroUsuarioSchema(BaseModel):
    nome_completo: str
    email: EmailStr
    cpf: str
    telefone: str
    senha: str
    cep_endereco: str
    veiculo: VeiculoSchema


class LoginSchema(BaseModel):
    login: str  # Pode ser Email ou CPF
    senha: str


# ==========================================
# FUNÇÕES AUXILIARES 
# ==========================================


def get_db():
    """Gerencia a sessão com o banco de dados por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validar_senha(senha: str) -> bool:
    """Garante no mínimo 4 caracteres e 2 letras."""
    if len(senha) < 4:
        return False
    letras = len(re.findall(r"[a-zA-Z]", senha))
    return letras >= 2


def sanitizar_numeros(texto: str) -> str:
    """Remove pontuações e mantém apenas números."""
    return re.sub(r"\D", "", texto)


# ==========================================
# APLICAÇÃO FASTAPI E ROTAS
# ==========================================

app = FastAPI(
    title="EV Charging Station API",
    description="API de cadastro, login e mapeamento para carregadores de veículos elétricos.",
    version="1.0.0",
)


@app.post("/api/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    dados: RegistroUsuarioSchema, db: Session = Depends(get_db)
):
    # 1. Validação de Senha
    if not validar_senha(dados.senha):
        raise HTTPException(
            status_code=400,
            detail="A senha deve ter no mínimo 4 caracteres e conter pelo menos 2 letras.",
        )

    # 2. Tratamento de campos
    email = dados.email.strip().lower()
    cpf = sanitizar_numeros(dados.cpf)
    telefone = sanitizar_numeros(dados.telefone)
    placa = dados.veiculo.placa.strip().upper()

    # 3. Verificação de Duplicatas
    if (
        db.query(UsuarioModel)
        .filter(UsuarioModel.email == email)
        .first()
    ):
        raise HTTPException(
            status_code=409, detail="Este e-mail já está cadastrado."
        )
    if db.query(UsuarioModel).filter(UsuarioModel.cpf == cpf).first():
        raise HTTPException(
            status_code=409, detail="Este CPF já está cadastrado."
        )
    if (
        db.query(UsuarioModel)
        .filter(UsuarioModel.telefone == telefone)
        .first()
    ):
        raise HTTPException(
            status_code=409, detail="Este telefone já está cadastrado."
        )
    if db.query(VeiculoModel).filter(VeiculoModel.placa == placa).first():
        raise HTTPException(
            status_code=409, detail="Esta placa já está cadastrada."
        )

    # 4. Criação do Usuário
    novo_usuario = UsuarioModel(
        nome_completo=dados.nome_completo,
        email=email,
        cpf=cpf,
        telefone=telefone,
        senha_hash=generate_password_hash(dados.senha),
        cep_endereco=dados.cep_endereco,
    )

    db.add(novo_usuario)
    db.flush()

    # 5. Criação do Veículo
    novo_veiculo = VeiculoModel(
        marca=dados.veiculo.marca,
        modelo_ano=dados.veiculo.modelo_ano,
        placa=placa,
        cor=dados.veiculo.cor,
        carroceria=dados.veiculo.carroceria,
        usuario_id=novo_usuario.id,
    )

    db.add(novo_veiculo)
    db.commit()

    return {
        "mensagem": "Usuário e veículo cadastrados com sucesso!",
        "usuario_id": novo_usuario.id,
    }


@app.post("/api/login")
def login(dados: LoginSchema, db: Session = Depends(get_db)):
    identificador_limpo = sanitizar_numeros(dados.login)

    # Busca usuário por Email ou por CPF
    usuario = (
        db.query(UsuarioModel)
        .filter(
            (UsuarioModel.email == dados.login.strip().lower())
            | (UsuarioModel.cpf == identificador_limpo)
        )
        .first()
    )

    if not usuario or not check_password_hash(
        usuario.senha_hash, dados.senha
    ):
        raise HTTPException(
            status_code=401, detail="Credenciais inválidas."
        )

    # Simulação de envio do código 2FA
    codigo_2fa = "123456"

    return {
        "mensagem": "Credenciais válidas. Digite o código enviado para o seu dispositivo.",
        "usuario_id": usuario.id,
        "codigo_dev_teste": codigo_2fa,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    app.run(debug=True)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///motoristas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de Motorista
class Motorista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Motorista {self.nome}>'

# Modelo de Contribuição
class Contribuicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey('motorista.id'), nullable=False)
    data_contribuicao = db.Column(db.DateTime, nullable=False)
    valor = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Contribuicao de Motorista ID {self.motorista_id}>'


# Rota Inicial
@app.route("/")
def home():
    return "Bem-vindo ao COPBRAZIL!"

from flask import request, jsonify

# Rota para cadastro de motoristas
@app.route("/cadastro", methods=["POST"])
def cadastro_motorista():
    dados = request.json

    # Validar campos obrigatórios
    if not all(key in dados for key in ("nome", "cpf", "telefone")):
        return jsonify({"erro": "Campos obrigatórios: nome, cpf, telefone"}), 400

    # Verificar se o CPF já está cadastrado
    motorista_existente = Motorista.query.filter_by(cpf=dados["cpf"]).first()
    if motorista_existente:
        return jsonify({"erro": "CPF já cadastrado"}), 400

    # Criar novo motorista
    novo_motorista = Motorista(
        nome=dados["nome"],
        cpf=dados["cpf"],
        telefone=dados["telefone"],
        email=dados.get("email")
    )

    # Salvar no banco de dados
    db.session.add(novo_motorista)
    db.session.commit()

    return jsonify({"mensagem": "Motorista cadastrado com sucesso!"}), 201

# Rota para listar motoristas
@app.route("/motoristas", methods=["GET"])
def listar_motoristas():
    motoristas = Motorista.query.all()
    lista_motoristas = [
        {
            "id": motorista.id,
            "nome": motorista.nome,
            "cpf": motorista.cpf,
            "telefone": motorista.telefone,
            "email": motorista.email,
        }
        for motorista in motoristas
    ]
    return jsonify(lista_motoristas), 200

# Rota para o painel administrativo
@app.route("/painel_administrativo", methods=["GET"])
def painel_administrativo():
    total_motoristas = Motorista.query.count()
    total_contribuicoes = Contribuicao.query.count()
    total_acumulado = db.session.query(db.func.sum(Contribuicao.valor)).scalar() or 0.0

    return jsonify({
        "total_motoristas": total_motoristas,
        "total_contribuicoes": total_contribuicoes,
        "total_acumulado": total_acumulado,
        "mensagem": "Painel Administrativo atualizado com contribuições."
    }), 200


from datetime import datetime

# Rota para registrar contribuição
@app.route("/contribuir", methods=["POST"])
def registrar_contribuicao():
    dados = request.json

    # Verificar campos obrigatórios
    if not all(key in dados for key in ("motorista_id", "valor")):
        return jsonify({"erro": "Campos obrigatórios: motorista_id, valor"}), 400

    # Verificar se o motorista existe
    motorista = Motorista.query.get(dados["motorista_id"])
    if not motorista:
        return jsonify({"erro": "Motorista não encontrado"}), 404

    # Criar nova contribuição
    nova_contribuicao = Contribuicao(
        motorista_id=dados["motorista_id"],
        data_contribuicao=datetime.now(),
        valor=dados["valor"]
    )

    # Salvar no banco de dados
    db.session.add(nova_contribuicao)
    db.session.commit()

    return jsonify({"mensagem": "Contribuição registrada com sucesso!"}), 201

# Rota para editar dados de um motorista
@app.route("/editar_motorista/<int:id>", methods=["PUT"])
def editar_motorista(id):
    dados = request.json

    # Verificar se o motorista existe
    motorista = Motorista.query.get(id)
    if not motorista:
        return jsonify({"erro": "Motorista não encontrado"}), 404

    # Atualizar os dados do motorista
    motorista.nome = dados.get("nome", motorista.nome)
    motorista.cpf = dados.get("cpf", motorista.cpf)
    motorista.telefone = dados.get("telefone", motorista.telefone)
    motorista.email = dados.get("email", motorista.email)

    # Salvar alterações no banco de dados
    db.session.commit()

    return jsonify({"mensagem": "Motorista atualizado com sucesso!"}), 200



# Rota para excluir um motorista
@app.route("/excluir_motorista/<int:id>", methods=["DELETE"])
def excluir_motorista(id):
    # Verificar se o motorista existe
    motorista = Motorista.query.get(id)
    if not motorista:
        return jsonify({"erro": "Motorista não encontrado"}), 404

    # Remover o motorista do banco de dados
    db.session.delete(motorista)
    db.session.commit()

    return jsonify({"mensagem": "Motorista excluído com sucesso!"}), 200


# Rota para relatórios de contribuições
@app.route("/relatorios", methods=["GET"])
def relatorios():
    relatorios = db.session.query(
        Motorista.nome,
        db.func.count(Contribuicao.id).label("total_contribuicoes"),
        db.func.sum(Contribuicao.valor).label("total_valor")
    ).join(Contribuicao, Motorista.id == Contribuicao.motorista_id).group_by(Motorista.id).all()

    resultado = [
        {
            "nome": relatorio[0],
            "total_contribuicoes": relatorio[1],
            "total_valor": relatorio[2] or 0.0
        }
        for relatorio in relatorios
    ]

    return jsonify(resultado), 200

# Rota para listar contribuições detalhadas
@app.route("/contribuicoes", methods=["GET"])
def listar_contribuicoes():
    # Filtros opcionais
    motorista_id = request.args.get("motorista_id")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    query = db.session.query(
        Contribuicao.id,
        Contribuicao.motorista_id,
        Motorista.nome,
        Contribuicao.data_contribuicao,
        Contribuicao.valor
    ).join(Motorista, Contribuicao.motorista_id == Motorista.id)

    # Aplicar filtros
    if motorista_id:
        query = query.filter(Contribuicao.motorista_id == motorista_id)
    if data_inicio:
        query = query.filter(Contribuicao.data_contribuicao >= data_inicio)
    if data_fim:
        query = query.filter(Contribuicao.data_contribuicao <= data_fim)

    resultados = query.all()

    contribuições = [
        {
            "id": contrib[0],
            "motorista_id": contrib[1],
            "nome": contrib[2],
            "data_contribuicao": contrib[3].strftime("%Y-%m-%d %H:%M:%S"),
            "valor": contrib[4]
        }
        for contrib in resultados
    ]

    return jsonify(contribuições), 200


# Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

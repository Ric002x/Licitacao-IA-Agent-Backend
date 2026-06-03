# Licitações RPA API

Plataforma de automação para busca e análise inteligente de licitações públicas usando RPA (Robotic Process Automation) e Inteligência Artificial.

## 📋 Sumário

- [Sobre](#sobre)
- [Features](#features)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [API Documentation](#api-documentation)
- [Banco de Dados](#banco-de-dados)
- [Docker](#docker)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

## Sobre

Este projeto é uma API REST desenvolvida com **FastAPI** que automatiza o processo de busca, scraping e análise de licitações públicas. Utiliza agentes de IA para análise detalhada e scoring automático das licitações, com suporte completo a autenticação, banco de dados PostgreSQL e containerização via Docker.

Você pode encontrar o Frontend em: [Licitacao-IA-Agent-Frontend](https://github.com/Ric002x/-Licitacao-IA-Agent-Frontend) 

### Principais Características Técnicas

- **Framework**: FastAPI (Python 3.14)
- **Banco de Dados**: PostgreSQL com SQLAlchemy ORM
- **Autenticação**: JWT (JSON Web Tokens)
- **RPA**: Selenium com Chromium para scraping
- **IA**: Agentes inteligentes para análise e classificação
- **Migrações**: Alembic para versionamento do schema
- **Container**: Docker e Docker Compose
- **CORS**: Habilitado para integração com frontends

## Features

✨ **Funcionalidades Principais**

- 🔐 **Autenticação Segura**: Sistema de login com JWT e criação automática de superusuário
- 🕷️ **Web Scraping Automático**: RPA com Selenium e Chromium para coleta de dados
- 🤖 **Análise de IA**: Agentes inteligentes para análise detalhada e scoring de licitações
- 📊 **Gerenciamento de Usuários**: CRUD completo com controle de status
- 🔍 **Filtros Avançados**: Busca e filtragem de licitações por múltiplos critérios
- 📈 **Rating e Scoring**: Sistema automático de avaliação de licitações
- 🗄️ **Migrações Automáticas**: Alembic para evolução segura do banco de dados
- 🐳 **Containerização**: Docker e Docker Compose para deploy simplificado
- 📚 **Documentação Interativa**: Swagger UI integrada ao FastAPI

## Pré-requisitos

Certifique-se de ter os seguintes itens instalados:

- **Python 3.14+**
- **Docker** e **Docker Compose** (opcional, para containerização)
- **pip** (gerenciador de pacotes Python)

### Verificar Versões

```bash
python --version
docker --version
docker-compose --version
```

## Instalação

### 1. Clonar o Repositório

```bash
git clone https://github.com/Ric002x/OCRMarkdownBackEnd.git
cd licitacoes_rpa_agente_fastapi
```

### 2. Criar Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# API
API_V1_STR=/api/v1
PROJECT_NAME=Licitações RPA API
PROJECT_VERSION=1.0.0

# Segurança
SECRET_KEY=sua-chave-secreta-super-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=tempo-de-expiração-do-token-em-minutos

# Banco de Dados
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=sua-senha-segura
DB_NAME=licitacoes_db
```

## Configuração

### Banco de Dados

O banco de dados PostgreSQL é inicializado automaticamente via Docker Compose com as variáveis configuradas no arquivo `.env`:

```bash
docker-compose up -d --build
```

### Migrações

```bash
# Visualizar status das migrações
alembic current

# Criar nova migração
alembic revision --autogenerate -m "Descrição da alteração"

# Executar todas as migrações pendentes
alembic upgrade head

# Voltar uma migração
alembic downgrade -1
```

## Uso

### Execução Local

```bash
# Desenvolvimento com reload automático
uvicorn main:api --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn main:api --host 0.0.0.0 --port 8000 --workers 4
```

A API estará disponível em: `http://localhost:8000`

### Acessar Documentação Interativa

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc


### Componentes Principais

#### 🔐 **Auth** (`app/api/routes/auth.py`)
- Login com JWT
- Gerenciamento de tokens

#### 🕷️ **Licitações** (`app/api/routes/licitacoes.py`)
- Listagem de licitações
- Busca com filtros
- Análise com IA
- Background tasks para RPA
z
#### 👥 **Users** (`app/api/routes/user.py`)
- CRUD de usuários

#### 🤖 **Agentes** (`app/service/agentes/`)
- **Agente Rating Detail**: Análise detalhada de licitações
- **Agente Rating Score**: Scoring automático

#### 🔄 **RPA** (`app/service/scrapping.py`)
- Web scraping com Selenium
- Coleta automática de dados
- Background tasks assíncronas

## API Documentation

### Endpoints Principais

#### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/auth/login` | Fazer login |
| `GET` | `/api/v1/auth/me` | Pegar dados do usuário autenticado |

#### Licitações

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/licitacoes/procurar` | Buscar por licitações |
| `GET` | `/api/v1/licitacoes/status/{request_id}` | Status da busca de licitações |
| `GET` | `/api/v1/licitacoes/resultado/{request_id}` | Obter as licitações encontradas após a busca |
| `POST` | `/api/v1/licitacoes/descricao_ia` | Solicitar descrição por IA para uma licitação |

#### Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/users/cirar` | Criar usuário |
| `PUT` | `/api/v1/users/atualizar` | Atualizar usuário |

### Modelos de Dados

#### User
```json
{
  "id": "uuid",
  "email": "usuario@email.com",
  "username": "usuario",
  "status": "active|inactive|suspended",
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### RpaScrapRequest
```json
{
  "id": "uuid",
  "title": "título da busca",
  "filter_payload": "filtros da busca",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### RpaScrapEvent
```json
{
  "request_id": "uuid",
  "step": "pending|processing|completed",
  "status": "pending|processing|success|failure|ocurrence",
  "message": "mensagem personalizada do evento",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### RpaScrapResult
```json
[{
  "id": "uuid",
  "payload": "descrição da licitação",
  "score": "nota da licitação",
  "rating_detail": "avaliação IA da licitação",
  "created_at": "2024-01-01T00:00:00Z"
}]
```

## Banco de Dados

### Schema Principal

#### Tabela: users
- `id` (UUID, Primary Key)
- `email` (String, Unique)
- `username` (String, Unique)
- `password` (String, Hashed)
- `status` (Enum: active, inactive, suspended)
- `is_superuser` (Boolean)
- `created_at`, `updated_at`, `deleted_at` (DateTime)

#### Tabela: rpa_scrap_requests
- `id` (UUID, Primary Key)
- `title` (String)
- `user_id` (FK -> users)
- `filter_payload` (JSON)
- `created_at`, `updated_at` (DateTime)

#### Tabela: rpa_scrap_results
- `id` (UUID, Primary Key)
- `request_id` (FK -> rpa_scrap_requests)
- `payload` (JSON)
- `created_at` (DateTime)

#### Tabela: rpa_scrap_event
- `id` (UUID, Primary Key)
- `request_id` (FK -> rpa_scrap_requests)
- `step` (String)
- `status` (String)
- `message` (String)
- `created_at` (DateTime)

#### Tabela: rpa_ia_rating
- `id` (UUID, Primary Key)
- `result_id` (FK -> rpa_scrap_results)
- `rating_detail` (Text)
- `score` (Float, 0-10)
- `created_at`, `updated_at`(DateTime)

### Convenções

- ✅ Usar UUIDs como chaves primárias
- ✅ Timestamps automáticos (created_at, updated_at)
- ✅ Soft deletes com deleted_at
- ✅ Índices em FKs e campos frequentemente filtrados
- ✅ Usar enums para status e estados

## Segurança

### Boas Práticas Implementadas

- 🔒 **JWT**: Tokens com expiração configurável
- 🔐 **Hash de Senhas**: bcrypt com salt aleatório
- 🛡️ **CORS**: Configurável por ambiente
- 🔑 **Environment Variables**: Chaves sensíveis em `.env`
- 🚫 **Validação**: Pydantic para validação de entrada

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `API_V1_STR` | `/api/v1` | Prefixo das rotas da API |
| `PROJECT_NAME` | Licitações RPA API | Nome do projeto |
| `SECRET_KEY` | INSECURE | Chave para assinar JWTs (MUDE!) |
| `ALGORITHM` | HS256 | Algoritmo de criptografia |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 21600 | Expiração do token (minutos) |
| `DB_HOST` | postgres | Host do PostgreSQL |
| `DB_PORT` | 5432 | Porta do PostgreSQL |
| `DB_USER` | postgres | Usuário do PostgreSQL |
| `DB_PASSWORD` | postgres | Senha do PostgreSQL |
| `DB_NAME` | licitacoes_db | Nome do banco de dados |

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](./LICENSE) para detalhes.

## Suporte

Para dúvidas, issues ou sugestões:

1. Abra uma [Issue](../../issues) no GitHub
2. Crie uma [Discussion](../../discussions)
3. Envie um email para: ricvenicius@gmail.com

# Contrato da API

## Base URL

```text
/api
```

## Autenticacao

A API utiliza JWT via Simple JWT.

Endpoints publicos atuais:

- `POST /api/auth/register/prestador/`
- `POST /api/auth/login/`

Endpoints autenticados futuros devem enviar o token de acesso no header:

```http
Authorization: Bearer <access_token>
```

## POST /api/auth/register/prestador/

Cadastra um prestador de servico e cria o usuario de acesso vinculado ao e-mail informado.

### Request

```json
{
  "razao_social": "Clinica Exemplo LTDA",
  "nome_fantasia": "Clinica Exemplo",
  "cnpj": "12.345.678/0001-90",
  "endereco": "Rua Central, 100",
  "nome_responsavel": "Maria Silva",
  "email": "prestador@example.com",
  "telefone": "(11) 99999-9999",
  "senha": "SenhaForte123"
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `razao_social` | string | Sim | Maximo 255 caracteres |
| `nome_fantasia` | string | Sim | Maximo 255 caracteres |
| `cnpj` | string | Sim | Formato `00.000.000/0000-00` ou 14 digitos; deve ser unico |
| `endereco` | string | Sim | Texto livre |
| `nome_responsavel` | string | Sim | Maximo 255 caracteres |
| `email` | string | Sim | E-mail valido; deve ser unico para login |
| `telefone` | string | Sim | Maximo 20 caracteres |
| `senha` | string | Sim | Minimo 8 caracteres e validada pelas regras de senha do Django |

### Response 201

```json
{
  "id": 1,
  "razao_social": "Clinica Exemplo LTDA",
  "nome_fantasia": "Clinica Exemplo",
  "cnpj": "12345678000190",
  "endereco": "Rua Central, 100",
  "nome_responsavel": "Maria Silva",
  "email": "prestador@example.com",
  "telefone": "(11) 99999-9999",
  "criado_em": "2026-05-06T20:30:00Z",
  "atualizado_em": "2026-05-06T20:30:00Z"
}
```

Observacoes:

- A senha nunca e retornada pela API.
- A senha e armazenada com hash pelo mecanismo nativo do Django.
- O CNPJ e salvo normalizado, apenas com digitos.
- O usuario criado recebe o perfil `PRESTADOR`.

### Response 400

Erros de validacao retornam os campos com mensagens.

Exemplo de CNPJ invalido:

```json
{
  "cnpj": [
    "CNPJ deve estar no formato 00.000.000/0000-00 ou conter 14 digitos."
  ]
}
```

Exemplo de e-mail ja cadastrado:

```json
{
  "email": [
    "Ja existe um usuario cadastrado com este e-mail."
  ]
}
```

## POST /api/auth/login/

Autentica um usuario por e-mail e senha e retorna um par de tokens JWT.

### Request

```json
{
  "email": "prestador@example.com",
  "senha": "SenhaForte123"
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `email` | string | Sim | E-mail cadastrado |
| `senha` | string | Sim | Senha do usuario |

### Response 200

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

### Response 400

Credenciais invalidas ou usuario inativo retornam erro de validacao.

Exemplo:

```json
{
  "non_field_errors": [
    "E-mail ou senha invalidos."
  ]
}
```

## Modelos Base

### Usuario

| Campo | Descricao |
| --- | --- |
| `email` | Identificador unico usado para login |
| `perfil` | `PRESTADOR`, `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` |
| `password` | Hash da senha gerenciado pelo Django |

### PrestadorEmpresa

| Campo | Descricao |
| --- | --- |
| `user` | Relacao 1:1 com o usuario |
| `razao_social` | Razao social da empresa |
| `nome_fantasia` | Nome fantasia da empresa |
| `cnpj` | CNPJ unico, salvo com 14 digitos |
| `endereco` | Endereco da empresa |
| `nome_responsavel` | Responsavel pelo cadastro |
| `email` | E-mail do prestador |
| `telefone` | Telefone de contato |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

# API de Convites de Organização

Documentação para o frontend consumir o sistema de convites e notificações do SmartQA.

---

## Visão geral do fluxo

```
Owner/Admin envia convite por e-mail
        ↓
Sistema envia e-mail com link: {FRONTEND_URL}/invites/{token}
        ↓
┌─────────────────────────────────────────────────────────┐
│ Usuário TEM conta?                                       │
│   SIM → notificação interna criada imediatamente        │
│   NÃO → convite fica pendente; quando o usuário se      │
│          cadastrar, a notificação é criada              │
└─────────────────────────────────────────────────────────┘
        ↓
Usuário aceita ou recusa via notificação interna (ou link)
        ↓
Se aceito → OrganizationMember criado automaticamente
```

---

## Endpoints de convite

### 1. Enviar convite (owner/admin)

```
POST /organization/{slug}/invite
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "email": "usuario@exemplo.com",
  "role": "member"   // "member" | "admin"
}
```

**Resposta 201:**
```json
{
  "status": true,
  "message": "Convite enviado com sucesso",
  "data": {
    "invitation_id": 42,
    "invited_email": "usuario@exemplo.com",
    "role": "member",
    "expires_at": "2026-04-05T12:00:00+00:00"
  }
}
```

---

### 2. Buscar informações do convite (público, sem autenticação)

Usado para exibir a tela de convite quando o usuário acessa o link do e-mail.

```
GET /organization/invitations/{token}
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Convite encontrado",
  "data": {
    "invitation_id": 42,
    "status": "pending",          // "pending" | "accepted" | "declined" | "expired"
    "organization_name": "Minha Empresa",
    "organization_slug": "minha-empresa",
    "organization_avatar_color": "#4f46e5",
    "invited_by_name": "João Silva",
    "role": "member",
    "expires_at": "2026-04-05T12:00:00+00:00",
    "invited_email": "usuario@exemplo.com"
  }
}
```

**Erros possíveis:**
- `404` — token não encontrado
- `410` — convite expirado

---

### 3. Aceitar ou recusar convite (requer autenticação)

O usuário precisa estar logado na conta cujo e-mail corresponde ao convite.

```
POST /organization/invitations/{token}/respond
Authorization: Bearer {token_jwt}
Content-Type: application/json

Body:
{
  "action": "accept"    // "accept" | "decline"
}
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Convite aceito com sucesso!",
  "data": {
    "status": "accepted"
  }
}
```

---

### 4. Listar convites da organização (owner/admin)

```
GET /organization/{slug}/invitations
Authorization: Bearer {token}
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Convites listados",
  "data": [
    {
      "id": 42,
      "invited_email": "usuario@exemplo.com",
      "role": "member",
      "status": "pending",     // "pending" | "accepted" | "declined" | "expired"
      "invited_by_name": "João Silva",
      "expires_at": "2026-04-05T12:00:00+00:00",
      "created_at": "2026-03-29T12:00:00+00:00"
    }
  ]
}
```

---

### 5. Cancelar convite pendente (owner/admin)

```
DELETE /organization/{slug}/invitations/{invitation_id}
Authorization: Bearer {token}
```

**Resposta:** `204 No Content`

---

## Endpoints de notificações

Notificações são exibidas em uma caixinha/sino no frontend. O usuário recebe uma notificação do tipo `organization_invite` quando é convidado para uma org.

### 1. Listar notificações do usuário logado

```
GET /notifications/
Authorization: Bearer {token}

Query params (opcionais):
  unread_only=true    // retornar apenas não lidas (padrão: false)
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Notificações recuperadas",
  "data": {
    "unread_count": 2,
    "notifications": [
      {
        "id": 10,
        "type": "organization_invite",
        "title": "Convite para Minha Empresa",
        "message": "João Silva te convidou para participar de Minha Empresa como member.",
        "is_read": false,
        "payload": {
          "invitation_id": 42,
          "organization_id": 7,
          "organization_name": "Minha Empresa",
          "organization_slug": "minha-empresa",
          "token": "abc123...",
          "role": "member",
          "inviter_name": "João Silva"
        },
        "created_at": "2026-03-29T12:00:00+00:00"
      }
    ]
  }
}
```

**Campo `payload` para `organization_invite`:**
| Campo | Tipo | Descrição |
|---|---|---|
| `invitation_id` | int | ID do convite |
| `organization_id` | int | ID da organização |
| `organization_name` | string | Nome da organização |
| `organization_slug` | string | Slug da organização |
| `token` | string | Token para aceitar/recusar via API |
| `role` | string | Papel proposto (`member` ou `admin`) |
| `inviter_name` | string | Nome de quem convidou |

---

### 2. Marcar notificação como lida

```
PATCH /notifications/{notification_id}/read
Authorization: Bearer {token}
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Notificação marcada como lida",
  "data": null
}
```

---

### 3. Marcar todas como lidas

```
POST /notifications/read-all
Authorization: Bearer {token}
```

**Resposta 200:**
```json
{
  "status": true,
  "message": "Todas as notificações foram marcadas como lidas",
  "data": null
}
```

---

### 4. Deletar notificação

```
DELETE /notifications/{notification_id}
Authorization: Bearer {token}
```

**Resposta:** `204 No Content`

---

## Fluxo de UI recomendado

### Ícone de sino / badge de notificações

1. Ao carregar o app, chame `GET /notifications/?unread_only=true` para obter `unread_count`.
2. Exiba o badge com `data.unread_count`.
3. Ao abrir o painel de notificações, chame `GET /notifications/` (sem filtro).
4. Para cada notificação do tipo `organization_invite`, exiba botões **Aceitar** e **Recusar**.
5. Ao clicar em **Aceitar** ou **Recusar**:
   - Chame `POST /organization/invitations/{payload.token}/respond` com `{ "action": "accept" }` ou `{ "action": "decline" }`.
   - Após sucesso, a notificação já é marcada como lida automaticamente pelo backend.
   - Recarregue a lista de notificações.

### Tela de convite via link de e-mail (`/invites/{token}`)

1. Chame `GET /organization/invitations/{token}` para exibir os detalhes do convite (sem auth).
2. Se `status !== "pending"`, exiba mensagem apropriada (já respondido, expirado).
3. Se o usuário não estiver logado, direcione para login/cadastro preservando o token (ex.: query param `?invite={token}` ou localStorage).
4. Após login/cadastro, chame `POST /organization/invitations/{token}/respond` com a ação do usuário.

### Polling ou WebSocket (recomendado)

Para manter o badge de notificações atualizado em tempo real, você pode:
- Fazer polling leve a cada 30–60s em `GET /notifications/?unread_only=true`.
- Ou implementar WebSocket/SSE no backend futuramente.

---

## Erros padrão

Todas as respostas seguem o padrão:
```json
{
  "status": false,
  "message": "Mensagem de erro legível",
  "data": null
}
```

| HTTP | Situação |
|---|---|
| 400 | Erro de validação / regra de negócio |
| 401 | Token JWT ausente ou inválido |
| 403 | Sem permissão (não é owner/admin, ou convite não é para sua conta) |
| 404 | Recurso não encontrado |
| 410 | Convite expirado |

# Prompt para Codex

Implemente o módulo `webhook-monitor-telegram` neste repositório seguindo a estrutura do pacote entregue.

Requisitos:

1. Criar middleware/módulo transversal para registrar tentativas de webhook.
2. Agrupar tentativas por `project_id + provider + webhook_name + event_key`.
3. Disparar alerta Telegram quando houver 5 tentativas consecutivas para a mesma chave, com intervalo entre 45 e 75 segundos.
4. Implementar cooldown de 30 minutos por chave para evitar spam.
5. Não enviar payload completo no Telegram.
6. Persistir tentativas, incidentes e cooldown em Firestore ou storage equivalente do projeto.
7. Criar testes automatizados cobrindo:
   - 5 tentativas qualificadas disparam alerta;
   - 4 tentativas não disparam;
   - gaps fora da faixa não disparam;
   - cooldown evita spam;
   - eventos diferentes não se misturam;
   - falha no Telegram não derruba o processamento do webhook.
8. Documentar variáveis de ambiente e modo de deploy.

Ordem de trabalho:
1. Integrar o core do monitor.
2. Conectar storage real do projeto.
3. Conectar Telegram.
4. Adicionar testes.
5. Atualizar documentação técnica do projeto.

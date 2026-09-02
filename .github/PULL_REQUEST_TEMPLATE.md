## O que foi feito

O problema principal era que os `event_id` processados ficavam somente em memória. Com isso, a idempotência era perdida após um restart e duas entregas simultâneas podiam aplicar o mesmo crédito mais de uma vez. Também não havia validação dos dados de entrada antes da gravação.

Para corrigir:

- tornei `event_id` a chave primária da tabela `applied_events`, deixando a garantia de unicidade persistida no SQLite;
- removi o controle de eventos processados que existia apenas em memória;
- iniciei a operação com `BEGIN IMMEDIATE`, fazendo com que entregas concorrentes disputem a escrita de forma segura, inclusive quando vêm de instâncias diferentes usando o mesmo arquivo de banco;
- mantive o registro do evento e a atualização do saldo na mesma transação;
- tratei a violação de unicidade como entrega duplicada, retornando `applied=False` sem alterar o saldo;
- validei `event_id`, `account_id` e `amount_cents` antes de abrir a transação, levantando `InvalidCreditError` sem gravar eventos inválidos;
- adicionei testes para entrega simultânea, concorrência entre duas instâncias e nova tentativa de um evento corrigido após uma rejeição.

## Como você provou que funciona

Executei a suíte completa localmente: todos os 9 testes passaram.

O teste de concorrência entre duas instâncias cria dois objetos `CreditLedger` apontando para o mesmo arquivo SQLite, sincroniza as threads com `threading.Barrier` e envia o mesmo evento ao mesmo tempo. Ele verifica que as duas chamadas terminam, apenas uma retorna `applied=True` e o saldo recebe um único crédito.

Também executei esse teste contra o código original: ele falhou como esperado, pois as duas instâncias aplicaram o evento (`2` aplicações em vez de `1`). Na implementação corrigida, o mesmo teste passou em 25 execuções consecutivas. Isso demonstra que o teste reproduz o problema original e que a correção funciona também com múltiplos workers compartilhando o banco.

## Uso de AI

Usei o OpenAI Codex para revisar os requisitos, analisar os riscos de concorrência no SQLite, ajudar a elaborar os testes adicionais e conferir o diff e os resultados da suíte.

Aceitei a combinação simples de restrição única no banco, transação com `BEGIN IMMEDIATE` e validação antes da escrita, porque ela cobre concorrência entre threads, processos e restarts sem mudar a interface pública. Também aceitei a sugestão de testar duas instâncias distintas e de garantir que exceções nas threads não produzissem um falso positivo.

Descartei adicionar dependências externas, locks mantidos apenas em memória e uma refatoração maior do módulo. Essas alternativas aumentariam a complexidade e não resolveriam tão bem o caso de múltiplos workers quanto a garantia transacional do próprio SQLite. Revisei e validei localmente todas as mudanças antes da entrega.

## Checklist

- [x] `pytest` passa localmente
- [x] Adicionei pelo menos 2 testes novos, um deles de concorrência
- [x] Não alterei as asserções dos testes existentes

## Vídeo

- Link: **[SUBSTITUIR PELO LINK DO VÍDEO DE 3–5 MINUTOS]**

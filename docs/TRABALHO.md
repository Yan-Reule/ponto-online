# Sistema de Registro de Ponto com Reconhecimento Facial

## Objetivo

Desenvolver uma aplicação que permita cadastrar funcionários e registrar sua jornada usando identificação facial. O projeto integra desenvolvimento web, API, banco de dados e inteligência artificial conforme solicitado na atividade.

## Tecnologias e responsabilidades

- **React:** telas de cadastro, registro e consulta; acesso à câmera usando `getUserMedia`; envio de fotos via `FormData`.
- **Python e Flask:** validação dos dados, processamento das solicitações e exposição da API REST.
- **DeepFace:** detecção de rosto com OpenCV, alinhamento e geração de vetores com Facenet512. A verificação compara vetores com distância cosseno e o limiar do próprio modelo.
- **SQLite:** persistência de funcionários, fotos, vetores faciais e marcações.
- **Waitress e Docker:** execução local da aplicação e reprodução do ambiente.

## Fluxo implementado

No cadastro, a interface envia nome, matrícula, cargo e fotografia. A API valida os campos e a imagem, corrige sua orientação, redimensiona e normaliza para JPEG. O DeepFace precisa detectar exatamente um rosto. A representação facial gerada é comparada com os cadastros para impedir duplicidade. Os dados são gravados em uma transação.

No ponto, a câmera captura uma nova foto. O backend gera sua representação e compara com os vetores cadastrados usando `DeepFace.verify`. Se não houver correspondência, ou houver mais de uma, a operação é recusada. Uma única identificação permite verificar a sequência da jornada e gravar funcionário, data, horário e tipo. A foto do ponto é descartada após o processamento.

## Modelagem

`employees`: `id`, `name`, `registration` (única), `role`, `photo`, `embedding`, `created_at`.

`punches`: `id`, `employee_id` (chave estrangeira), `kind`, `occurred_at`.

Um funcionário possui vários registros. As fotos ficam como BLOB no SQLite. A relação é protegida por chave estrangeira e as gravações usam transações. Nome, matrícula e cargo aparecem no histórico por associação com o funcionário.

## Regras de negócio

1. Nome, matrícula, cargo e fotografia são obrigatórios.
2. A matrícula e o rosto não podem duplicar um cadastro existente.
3. São aceitas imagens JPEG, PNG e WebP até 5 MB e 16 megapixels.
4. Apenas uma face é aceita por imagem.
5. Um rosto desconhecido ou ambíguo não gera registro.
6. A jornada inicia por entrada, permite intervalo seguido de retorno e termina na saída.
7. Registros com menos de 30 segundos de diferença são rejeitados para evitar cliques duplicados.
8. Horários são definidos pelo servidor, com apresentação em UTC−03:00.

## Atendimento ao enunciado

| Requisito do PDF | Implementação |
| --- | --- |
| Cadastro React com nome, matrícula, cargo e foto | Tela Funcionários |
| Processamento em Python | API Flask |
| Reconhecimento com DeepFace | `FaceService.embedding` e `FaceService.matches` |
| Captura da câmera no ponto | Componente `PhotoCapture` |
| Identificação do funcionário | Verificação facial sem seleção manual de pessoa |
| Data, horário e tipo no banco | Tabela `punches` |
| Entrada, saída ou intervalo | Entrada, intervalo, retorno e saída |

## Validação e apresentação

Os testes automatizados verificam persistência, duplicidades, tipos inválidos, jornada completa, rosto desconhecido, ambiguidade, limite de imagem, filtros e jornada noturna. Usam um adaptador facial controlado para isolar as regras de negócio. A precisão real precisa ser avaliada com câmera e modelo carregado.

Na apresentação, explique o problema, mostre o cadastro de um voluntário, registre entrada, consulte o histórico e demonstre a rejeição de uma sequência inválida. Mostre o papel do React, do Python, do DeepFace e do banco em cada etapa. Não apresente testes com adaptador como evidência de precisão do reconhecimento real.

## Limitações e melhorias futuras

O protótipo não possui autenticação, vivacidade, ajuste administrativo de marcações ou cálculo de horas. Para evolução, implementar controle de acesso, proteção dos dados biométricos, avaliação de falsos positivos e negativos, política de retenção e um método de busca vetorial para bases maiores.

## Referências

- DeepFace: https://github.com/serengil/deepface
- React: https://react.dev/
- Flask: https://flask.palletsprojects.com/
- SQLite: https://www.sqlite.org/docs.html

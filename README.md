# PontoFace

Sistema acadêmico de registro de ponto por reconhecimento facial, desenvolvido conforme o **Trabalho Avaliativo** fornecido. Interface em React, API em Python/Flask, reconhecimento com DeepFace e banco SQLite.

## Executar com Docker (recomendado)

Instale e inicie Docker com Compose. Na pasta do projeto:

```sh
docker compose up --build -d
```

Abra **http://localhost:8000**. No Windows, também é possível executar `assistente.bat`. A primeira construção baixa dependências grandes de IA e pode levar vários minutos. O primeiro cadastro baixa o modelo Facenet512; mantenha internet disponível e aguarde. Os usos seguintes aproveitam o cache no volume `face-models`.

No Linux, execute `./iniciar.sh`. O script funciona também quando o Docker está instalado sem o plugin Compose, usando `docker build` e `docker run` diretamente. Nesse caso, o cache fica no volume `pontoface-models` e Ctrl+C encerra a aplicação.

```sh
docker compose logs -f       # acompanhar a execução
docker compose down          # parar; mantém os dados e o cache
```

Os cadastros, fotos, representações faciais e pontos ficam em `data/ponto.sqlite3`. O Compose expõe o serviço apenas na máquina local.

## Executar sem Docker

Use **Python 3.11** e **Node.js 22**. O ambiente de IA foi fixado para Python 3.11; não use Python 3.14 com estas versões de TensorFlow. No Linux Debian/Ubuntu, instale também `libgl1` e `libglib2.0-0` pelo gerenciador do sistema.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
python main.py
```

No Windows, use `py -3.11 -m venv .venv` e `.venv\Scripts\activate` em vez dos dois primeiros comandos. Abra http://localhost:8000.

Para desenvolver a interface, mantenha `python main.py` aberto e execute `npm run dev` em `frontend/`, em outro terminal. O Vite encaminha `/api` ao Python na porta 8000.

## Usar e apresentar

1. Abra **Funcionários** e preencha nome, matrícula e cargo.
2. Ative a câmera e capture uma foto frontal, ou envie JPEG/PNG/WebP de até 5 MB e 16 megapixels. Apenas um rosto pode aparecer.
3. Confirme o cadastro. A API detecta o rosto, gera sua representação numérica e armazena os dados e a foto.
4. Abra **Registrar ponto**, ative a câmera e capture uma nova foto.
5. Selecione **Entrada** e confirme. O DeepFace compara o rosto com os cadastros. Somente uma correspondência inequívoca permite gravar o ponto.
6. Consulte **Histórico de pontos**, com filtro por data, nome ou matrícula.
7. Demonstre **Intervalo → Retorno → Saída**, respeitando 30 segundos entre registros. Também é permitido **Entrada → Saída** sem intervalo.

O horário vem do servidor e é armazenado com fuso UTC. A API e a interface exibem o fuso de Araguaína (UTC−03:00). A sequência continua válida em jornadas que atravessam a meia-noite. A fotografia enviada ao registrar ponto não é persistida; apenas a fotografia cadastral é armazenada.

## Estrutura

```text
backend/app.py       API, validação, SQLite e regras de jornada
backend/face.py      integração real com DeepFace
frontend/src/       interface React responsiva e câmera
main.py             servidor local Waitress
tests/test_app.py   testes de integração da API com reconhecimento controlado
docs/TRABALHO.md    descrição técnica e roteiro de apresentação
Dockerfile          build da interface e ambiente Python 3.11
compose.yaml        execução com persistência
```

## API

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/api/health` | Disponibilidade da API (não verifica o carregamento do modelo) |
| GET | `/api/employees` | Listar funcionários sem dados biométricos |
| POST | `/api/employees` | Cadastrar com multipart: `name`, `registration`, `role`, `photo` |
| GET | `/api/employees/:id/photo` | Foto cadastral |
| POST | `/api/punches` | Identificar e registrar; multipart: `photo`, `kind` |
| GET | `/api/punches?date=2026-10-21` | Histórico, com data opcional |

Tipos: `entrada`, `intervalo`, `retorno`, `saida`. Erros retornam JSON `{ "error": "mensagem" }` e status HTTP adequado. O sistema não oferece registro manual que contorne a identificação facial.

## Testes

Os testes das regras não precisam instalar TensorFlow ou baixar modelos:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-base.txt
python -m unittest discover -s tests -v
cd frontend
npm ci
npm run build
```

O adaptador facial controlado é injetado somente pelos testes. A aplicação normal sempre usa DeepFace. Testes de API não medem a precisão biométrica: faça a demonstração com a câmera real, testando um funcionário cadastrado, uma pessoa não cadastrada e uma foto sem rosto.

Os resultados executados estão em [docs/VALIDACAO.md](docs/VALIDACAO.md). O roteiro técnico para apresentação está em [docs/TRABALHO.md](docs/TRABALHO.md).

## Escopo e limitações

Protótipo acadêmico para execução local, sem autenticação administrativa e sem detecção de vivacidade: uma fotografia pode ser apresentada à câmera. Não é um produto pronto para controle de jornada em produção. A comparação usa Facenet512, distância cosseno e limiar padrão do DeepFace; não interpreta a distância como probabilidade. Compara os vetores com todos os funcionários, adequado para uma pequena turma de demonstração. Fotos e vetores são dados sensíveis: use voluntários e mantenha o banco local. A implementação não calcula folha de pagamento ou horas trabalhadas.

A câmera funciona em `localhost` ou HTTPS e exige permissão do navegador. Sem câmera, o cadastro permite upload, mas o registro de ponto exige a captura. O erro de modelo indisponível deve ser investigado com os logs; não há simulação automática de sucesso.

Referências: [DeepFace](https://github.com/serengil/deepface), [Flask](https://flask.palletsprojects.com/), [React](https://react.dev/), [MediaDevices.getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

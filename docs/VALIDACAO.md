# Validação realizada

Verificação em 21/10/2026.

| Verificação | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -v` | 11 testes passaram |
| `npm run build` | Interface compilada com Vite 6.4.5 |
| Auditoria após instalação das dependências npm | Nenhuma vulnerabilidade reportada |
| `docker build -t pontoface:local .` | Imagem construída com Python 3.11 e dependências reais |
| Importação do DeepFace no Docker | Passou |
| Cadastro, reconhecimento e registro usando DeepFace real | Passou em banco temporário |
| Rejeição de imagem branca sem rosto | HTTP 422, sem criação de ponto |
| Chrome headless com câmera simulada | Navegação, captura, preenchimento e erro de banco vazio passaram |
| Interface em 1440 px e 390 px | Sem erros JavaScript e sem transbordamento horizontal da página |

O teste real utilizou `img1.jpg` do [conjunto de teste do DeepFace v0.0.93](https://github.com/serengil/deepface/tree/v0.0.93/tests/dataset) e o modelo Facenet512. O mesmo arquivo foi usado no cadastro e na verificação: isso comprova a integração, mas não mede precisão entre capturas distintas. O banco desse teste foi temporário e não alterou os cadastros da aplicação.

Não foi testada uma webcam física. A demonstração final deve cadastrar um voluntário e capturar outra foto ao registrar ponto, incluindo tentativas com uma pessoa não cadastrada. O projeto não possui teste de vivacidade.

Para repetir a verificação real após instalar todas as dependências:

```sh
python -m tests.smoke_deepface /caminho/para/uma/foto.jpg
```

O script cria e elimina seu próprio banco temporário. Ele não altera o banco normal. O primeiro uso exige download dos pesos.

Capturas da interface: [desktop](interface-desktop.png) e [celular](interface-mobile.png).

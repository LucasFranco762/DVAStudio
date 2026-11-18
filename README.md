# DVA Studio Desktop

Versão desktop em Python/PyQt6 inspirada no app Android MusicVideoApp.

## O que o programa faz

- Abre o YouTube ou outro site de vídeo em um navegador integrado.
- Detecta URLs de vídeo.
- Permite voltar à página anterior pelo botão à esquerda da URL ou por Alt+Esquerda.
- Permite baixar em três modos: vídeo + áudio, somente áudio ou somente vídeo.
- Mostra progresso em tempo real.
- Mantém o navegador ativo durante a escolha do destino, o download e a confirmação de conclusão.
- Lista os arquivos baixados.
- Abre a pasta de downloads ou reproduz o arquivo com o player padrão do sistema.

> Use apenas para baixar conteúdos próprios, autorizados ou livres de direitos. Respeite os termos das plataformas e a legislação aplicável.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Downloads de áudio e vídeo

O navegador integrado usa a página desktop do YouTube e a política de reprodução
desktop do WebEngine. No Windows, a composição usa software para evitar falhas
de compartilhamento de texturas D3D/Skia que podem deixar a página preta.
As janelas de conclusão são exibidas sem tomar o foco do player.

Para testar a reprodução até o fim com download simultâneo, usando vídeo local
e verificando também a imagem exibida e a pausa manual:

```powershell
.venv\Scripts\python.exe tests/verify_video_playback.py
```

O FFmpeg para conversão e mesclagem já acompanha o pacote `imageio-ffmpeg`.
Para baixar do YouTube, instale [Deno](https://deno.com/) (2.3 ou superior)
ou [Node.js](https://nodejs.org/) (22 ou superior) e deixe-o no PATH.
O programa aceita ambos e inclui os scripts `yt-dlp-ejs` pela dependência
`yt-dlp[default]`, conforme a [documentação do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

Para atualizar os componentes de download no ambiente virtual:

```bash
python -m pip install --upgrade -r requirements.txt
```

## Gerar o executável Windows

Na raiz do projeto, execute:

```powershell
python Gerar_executavel.py
```

O gerador usa a `.venv` do projeto quando disponível (ou cria `.venv-build`), confere/instala as
dependências de `requirements-build.txt` e gera `dist/DVAStudio.exe` em modo
**one-folder**, com os arquivos necessários ao lado do executável. Node.js 22
ou superior deve estar instalado apenas no computador que faz a compilação.
O gerador inclui esse Node.js, FFmpeg, Python, Qt/WebEngine e os componentes do
yt-dlp na distribuição; o computador de destino não precisa instalá-los.
Na primeira compilação, é necessário acesso à internet para obter a licença
da versão do Node incluída e eventuais dependências ausentes.

A pasta `dist` anterior é substituída somente após os testes do novo
executável. Feche o aplicativo antes de gerar uma nova versão. Se a compilação
ou a validação falhar, a distribuição anterior permanece disponível.
Os logs ficam em `build/gerar_executavel.log` e o resultado da validação em
`build/verificacao_distribuicao.json`. A validação executa o aplicativo com um
PATH sem Python, Node ou FFmpeg externos e testa navegador, ícones e conversão MP3.

Distribua **toda a pasta `dist`**, sem mover apenas o `.exe`. A distribuição é
para Windows 10/11 de 64 bits e mantém o ícone definido em `Icone.ico`/`Icone.png`.
Não é um executável para macOS ou Linux.

O projeto atualmente não usa banco de dados nem `config.json`. As preferências
continuam em `%APPDATA%/DVAStudio/settings.ini`, preservando a pasta de downloads
já configurada. Se houver `config.json` na distribuição anterior ou na raiz do
projeto, o gerador o copia sem alterar seus valores para junto do novo executável;
o arquivo da distribuição anterior tem prioridade.

Verificação de download e conversão MP3, sem acesso a sites externos:

```bash
python -m unittest discover -s tests -v
```

## Estrutura

```text
Gerar_executavel.py              geração e validação do executável
src/dvaStudio/app.py             inicialização
src/dvaStudio/core/downloader.py worker de download com yt-dlp
src/dvaStudio/ui/main_window.py  interface principal
src/dvaStudio/ui/styles.py       tema visual moderno
Icone.png / Icone.ico            ícones do aplicativo e executável
```

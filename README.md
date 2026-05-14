# NeonWave Desktop

Versão desktop em Python/PyQt6 inspirada no app Android MusicVideoApp.

## O que o programa faz

- Abre o YouTube ou outro site de vídeo em um navegador integrado.
- Detecta URLs de vídeo.
- Permite baixar em três modos: vídeo + áudio, somente áudio ou somente vídeo.
- Mostra progresso em tempo real.
- Lista os arquivos baixados.
- Abre a pasta de downloads ou reproduz o arquivo com o player padrão do sistema.

> Use apenas para baixar conteúdos próprios, autorizados ou livres de direitos. Respeite os termos das plataformas e a legislação aplicável.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Requisito recomendado

Instale o FFmpeg e deixe-o disponível no PATH para melhor compatibilidade com mesclagem/conversão de áudio e vídeo.

## Estrutura

```text
src/neonwave/app.py              inicialização
src/neonwave/core/downloader.py  worker de download com yt-dlp
src/neonwave/ui/main_window.py   interface principal
src/neonwave/ui/styles.py        tema visual moderno
src/neonwave/assets/icon.svg     ícone vetorial base
```

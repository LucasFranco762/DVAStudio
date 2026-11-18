"""Gera dist/DVAStudio.exe e suas dependências: python Gerar_executavel.py."""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
DIST = ROOT / "dist"


def _managed_path(path: Path) -> Path:
    """Valida o destino antes de remover ou mover pastas do projeto."""
    path = path.absolute()
    if path == ROOT or not path.is_relative_to(ROOT):
        raise RuntimeError(f"Caminho fora do projeto: {path}")
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise RuntimeError(f"Pasta redirecionada não permitida: {part}")
    if not path.resolve().is_relative_to(ROOT):
        raise RuntimeError(f"Destino fora do projeto: {path}")
    return path


def _remove(path: Path) -> None:
    path = _managed_path(path)
    if path.exists():
        shutil.rmtree(path)


def _python() -> Path:
    local = ROOT / ".venv" / "Scripts" / "python.exe"
    if local.is_file():
        return local
    environment = _managed_path(ROOT / ".venv-build")
    python = environment / "Scripts" / "python.exe"
    if not python.is_file():
        print("Criando ambiente isolado para compilação...", flush=True)
        _run([sys.executable, "-m", "venv", str(environment)])
    return python


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def _dependencies(python: Path) -> None:
    print("Conferindo as dependências de compilação...", flush=True)
    _run([str(python), "-m", "pip", "--disable-pip-version-check", "install",
          "-r", str(ROOT / "requirements-build.txt")])
    _run([str(python), "-m", "pip", "check"])


def _prepare_runtime(python: Path) -> Path:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Instale Node.js 22 ou superior no computador de compilação e execute novamente.")
    version = _run([node, "--version"], capture_output=True, text=True).stdout.strip()
    if int(version.lstrip("v").split(".")[0]) < 22:
        raise RuntimeError(f"Node.js {version} incompatível. Instale a versão 22 ou superior.")
    runtime = _managed_path(BUILD / "runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copy2(node, runtime / "node.exe")
    ffmpeg = _run([
        str(python), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())",
    ], capture_output=True, text=True).stdout.strip()
    shutil.copy2(ffmpeg, runtime / "ffmpeg.exe")
    # Mantém os avisos de licença correspondentes ao Node que será distribuído.
    license_file = runtime / f"Node-{version}-LICENSE.txt"
    if not license_file.is_file():
        url = f"https://raw.githubusercontent.com/nodejs/node/{version}/LICENSE"
        print(f"Obtendo licença do Node.js {version}...", flush=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            contents = response.read()
        license_file.write_bytes(contents)
    return runtime


def _preserve_config(destination: Path) -> None:
    # O programa ainda não usa config.json. Se existir, preserva o arquivo
    # sem reescrever valores; a configuração da distribuição anterior prevalece.
    candidates = [DIST / "config.json", DIST / "DVAStudio" / "config.json", ROOT / "config.json"]
    for source in candidates:
        if source.is_file():
            shutil.copy2(source, destination / "config.json")
            print(f"Configuração preservada: {source}", flush=True)
            break


def _replace_dist(new_dist: Path) -> None:
    new_dist = _managed_path(new_dist)
    _managed_path(DIST)
    backup = _managed_path(BUILD / f"dist-anterior-{uuid.uuid4().hex}")
    had_previous = DIST.exists()
    if had_previous:
        DIST.rename(backup)
    try:
        new_dist.rename(DIST)
    except OSError:
        if had_previous:
            backup.rename(DIST)
        raise
    if had_previous:
        try:
            _remove(backup)
        except OSError:
            print(f"A versão anterior está em uso. Cópia antiga mantida em: {backup}", flush=True)


def _build(python: Path, stage: Path, runtime: Path) -> Path:
    env = os.environ.copy()
    env["DVASTUDIO_BUILD_RUNTIME"] = str(runtime)
    log_file = BUILD / "gerar_executavel.log"
    print(f"Gerando aplicativo one-folder. Log: {log_file}", flush=True)
    with log_file.open("w", encoding="utf-8") as log:
        process = subprocess.Popen([
            str(python), "-m", "PyInstaller", str(ROOT / "DVAStudio.spec"),
            "--noconfirm", "--distpath", str(stage),
            "--workpath", str(BUILD / "pyinstaller"),
        ], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        if process.wait() != 0:
            raise RuntimeError(f"A compilação falhou. Consulte {log_file}")
    return stage / "DVAStudio"


def _verify(new_dist: Path) -> None:
    report = BUILD / "verificacao_distribuicao.json"
    if report.exists():
        report.unlink()
    env = os.environ.copy()
    # A verificação não deve encontrar Python, FFmpeg ou Node instalados no PATH.
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    env["PATH"] = os.pathsep.join([str(windows / "System32"), str(windows)])
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["QT_QPA_PLATFORM"] = "offscreen"
    print("Verificando o executável com as dependências da própria distribuição...", flush=True)
    process = subprocess.run([
        str(new_dist / "DVAStudio.exe"), "--verificar-distribuicao", str(report),
    ], cwd=BUILD, env=env, timeout=90)
    if process.returncode:
        details = report.read_text(encoding="utf-8") if report.exists() else "Sem relatório de diagnóstico."
        raise RuntimeError(f"Verificação terminou com código {process.returncode}: {details}")
    result = json.loads(report.read_text(encoding="utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Falha na verificação do executável: {result}")
    print("Verificação aprovada: Qt/WebEngine, ícones, Node.js, FFmpeg e conversão MP3.", flush=True)


def main() -> int:
    try:
        if os.name != "nt":
            raise RuntimeError("Execute este gerador no Windows para criar o aplicativo Windows.")
        if struct.calcsize("P") != 8:
            raise RuntimeError("Use Python de 64 bits para gerar esta distribuição Windows x64.")
        _managed_path(DIST)
        _managed_path(BUILD)
        BUILD.mkdir(exist_ok=True)
        python = _python()
        print(f"Ambiente de compilação: {python}", flush=True)
        _dependencies(python)
        runtime = _prepare_runtime(python)
        _run([str(python), "-m", "compileall", "-q", "src", "main.py", "Gerar_executavel.py"])
        _run([str(python), "-m", "unittest", "discover", "-s", "tests", "-v"])
        # mkdir herda as permissões normais do projeto. No Windows, mkdtemp
        # cria uma ACL privada que seria mantida ao mover a pasta para dist.
        stage = _managed_path(BUILD / f"distribuicao-{uuid.uuid4().hex}")
        stage.mkdir()
        try:
            new_dist = _build(python, stage, runtime)
            _verify(new_dist)
            _preserve_config(new_dist)
            _replace_dist(new_dist)
        finally:
            _remove(stage)
        print(f"\nExecutável gerado: {DIST / 'DVAStudio.exe'}", flush=True)
        print("Distribua a pasta dist completa. Python, Node.js e FFmpeg já estão incluídos.", flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"\nNão foi possível gerar o executável: {exc}", file=sys.stderr)
        print("Feche o aplicativo se estiver em uso e tente novamente. A versão anterior é preservada em caso de falha na compilação.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

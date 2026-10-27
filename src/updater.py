"""
Cross-platform auto-updater for Job Hunter.
Supports Windows, Linux, and macOS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Project root directory (directory containing start.sh and start.bat)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_npm_executable() -> str:
    """Return npm command path, accounting for Windows cmd extensions."""
    if sys.platform == "win32":
        cmd = shutil.which("npm.cmd") or shutil.which("npm")
        return cmd or "npm"
    return shutil.which("npm") or "npm"


def is_git_available() -> bool:
    """Check if git command is installed and accessible on PATH."""
    return shutil.which("git") is not None


def is_git_repo(root: Path) -> bool:
    """Check if directory is inside a valid git working tree."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0 and res.stdout.strip() == "true"
    except (subprocess.SubprocessError, OSError):
        return False


def get_current_branch(root: Path) -> Optional[str]:
    """Get active git branch name."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            branch = res.stdout.strip()
            return branch if branch != "HEAD" else None
        return None
    except (subprocess.SubprocessError, OSError):
        return None


def get_upstream_branch(root: Path) -> Optional[str]:
    """Get configured upstream tracking branch (e.g. origin/main)."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.stdout.strip() if res.returncode == 0 else None
    except (subprocess.SubprocessError, OSError):
        return None


def has_local_uncommitted_changes(root: Path) -> bool:
    """Check if there are uncommitted changes in tracked files."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "-uno"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0 and bool(res.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return False


def get_diff_files(root: Path, old_commit: str, new_commit: str) -> List[str]:
    """List paths of files modified between two commits."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", old_commit, new_commit],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return []
    except (subprocess.SubprocessError, OSError):
        return []


def check_and_apply_updates(root: Optional[Path] = None, timeout_seconds: int = 15) -> bool:
    """
    Check for upstream git updates and fast-forward cleanly.
    Returns True if updates were pulled, False otherwise.
    Safe across Windows, macOS, and Linux.
    """
    if root is None:
        root = PROJECT_ROOT

    if not is_git_available():
        print("[*] Git no esta disponible en PATH. Se omite comprobacion de actualizaciones.")
        return False

    if not is_git_repo(root):
        print("[*] La carpeta no es un repositorio Git. Se omite comprobacion de actualizaciones.")
        return False

    branch = get_current_branch(root)
    upstream = get_upstream_branch(root)

    if not upstream:
        if branch:
            print(f"[*] Rama actual: {branch} (sin seguimiento remoto configurado). Se omite auto-actualizacion.")
        return False

    if has_local_uncommitted_changes(root):
        print("[!] Hay cambios locales sin confirmar en archivos del repositorio. Se conserva la version local.")
        return False

    try:
        # Get commit before pull
        head_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if head_proc.returncode != 0:
            return False
        prev_head = head_proc.stdout.strip()

        print(f"[*] Comprobando actualizaciones remotas ({upstream})...")
        pull_proc = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        if pull_proc.returncode != 0:
            err_msg = pull_proc.stderr.strip() or pull_proc.stdout.strip()
            # If network error or no connection, inform without breaking startup
            if any(term in err_msg.lower() for term in ["could not resolve", "connection", "timed out", "fatal"]):
                print("[!] Sin conexion con el repositorio remoto. Continuando con la version local.")
            else:
                print(f"[!] No se pudo aplicar fast-forward: {err_msg}. Continuando con la version local.")
            return False

        # Get commit after pull
        new_head_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        new_head = new_head_proc.stdout.strip() if new_head_proc.returncode == 0 else prev_head

        if prev_head == new_head:
            print("[OK] El proyecto esta actualizado a la ultima version.")
            return False

        print(f"[OK] Actualizacion aplicada con exito ({prev_head[:7]} -> {new_head[:7]}).")
        diff_files = get_diff_files(root, prev_head, new_head)

        # 1. Check Python dependencies update
        if "requirements.txt" in diff_files:
            print("[*] Cambios detectados en requirements.txt. Actualizando dependencias de Python...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=str(root),
                    check=False,
                    timeout=120,
                )
            except Exception as e:
                print(f"[!] Aviso al instalar dependencias de Python: {e}")

        # 2. Check Web frontend dependencies update
        web_pkg = "web/package.json" in diff_files or "web/package-lock.json" in diff_files
        npm_bin = get_npm_executable()
        web_dir = root / "web"

        if web_pkg and web_dir.exists():
            print("[*] Cambios detectados en web/package.json. Instalando paquetes npm...")
            try:
                subprocess.run(
                    [npm_bin, "install"],
                    cwd=str(web_dir),
                    check=False,
                    timeout=180,
                )
            except Exception as e:
                print(f"[!] Aviso al ejecutar npm install: {e}")

        # 3. Check Web frontend rebuild
        needs_build = any(f.startswith("web/") and not f.startswith("web/dist/") for f in diff_files)
        if needs_build and web_dir.exists():
            print("[*] Cambios detectados en la interfaz web. Recompilando frontend...")
            try:
                subprocess.run(
                    [npm_bin, "run", "build"],
                    cwd=str(web_dir),
                    check=False,
                    timeout=180,
                )
                print("[OK] Frontend recompilado con exito.")
            except Exception as e:
                print(f"[!] Aviso al compilar el frontend: {e}")

        return True

    except subprocess.TimeoutExpired:
        print("[!] Tiempo de espera agotado al conectar con el repositorio. Continuando con la version local.")
        return False
    except Exception as e:
        print(f"[!] Error inesperado durante la comprobacion de actualizaciones: {e}")
        return False


def main() -> int:
    """Entry point for python -m src.updater"""
    check_and_apply_updates()
    return 0


if __name__ == "__main__":
    sys.exit(main())

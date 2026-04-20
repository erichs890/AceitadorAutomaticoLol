"""
Interface gráfica do Auto-Aceitar LoL.

Faz tudo pro usuário leigo:
  1. Verifica o Python.
  2. Instala as dependências do requirements.txt (se faltarem).
  3. Inicia / para o script auto_aceitar.py com um clique.
  4. Mostra o log em tempo real dentro da janela.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext

PASTA = Path(__file__).parent.resolve()
REQUIREMENTS = PASTA / "requirements.txt"
SCRIPT = PASTA / "auto_aceitar.py"
PASTA_IMAGENS = PASTA / "imagens"

PACOTES = ["mss", "cv2", "numpy", "pyautogui"]  # nomes de import
PACOTES_PIP = {
    "mss": "mss",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "pyautogui": "pyautogui",
}


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Auto-Aceitar LoL")
        self.root.geometry("720x520")
        self.root.minsize(560, 420)

        self.processo: subprocess.Popen | None = None
        self.fila_log: queue.Queue[str] = queue.Queue()
        self.thread_leitora: threading.Thread | None = None

        self._montar_ui()
        self._verificar_arquivos()
        self.root.after(100, self._drenar_log)
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    # ---------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        fonte_titulo = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        fonte_botao = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        fonte_normal = tkfont.Font(family="Segoe UI", size=10)

        topo = tk.Frame(self.root, padx=16, pady=14)
        topo.pack(fill="x")

        tk.Label(topo, text="Auto-Aceitar LoL", font=fonte_titulo).pack(anchor="w")
        tk.Label(
            topo,
            text=(
                "1) Clique em INSTALAR (apenas na primeira vez).\n"
                "2) Clique em INICIAR antes de entrar na fila.\n"
                "3) O programa para sozinho ao entrar na seleção de campeões."
            ),
            font=fonte_normal,
            justify="left",
            fg="#444",
        ).pack(anchor="w", pady=(4, 0))

        botoes = tk.Frame(self.root, padx=16, pady=4)
        botoes.pack(fill="x")

        self.btn_instalar = tk.Button(
            botoes,
            text="INSTALAR DEPENDÊNCIAS",
            font=fonte_botao,
            bg="#2b6cb0",
            fg="white",
            activebackground="#2c5282",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=8,
            command=self._ao_clicar_instalar,
        )
        self.btn_instalar.pack(side="left")

        self.btn_iniciar = tk.Button(
            botoes,
            text="INICIAR",
            font=fonte_botao,
            bg="#2f855a",
            fg="white",
            activebackground="#276749",
            activeforeground="white",
            relief="flat",
            padx=22,
            pady=8,
            command=self._ao_clicar_iniciar,
        )
        self.btn_iniciar.pack(side="left", padx=(8, 0))

        self.btn_parar = tk.Button(
            botoes,
            text="PARAR",
            font=fonte_botao,
            bg="#c53030",
            fg="white",
            activebackground="#9b2c2c",
            activeforeground="white",
            relief="flat",
            padx=22,
            pady=8,
            state="disabled",
            command=self._ao_clicar_parar,
        )
        self.btn_parar.pack(side="left", padx=(8, 0))

        self.lbl_status = tk.Label(
            botoes, text="● Parado", font=fonte_botao, fg="#c53030"
        )
        self.lbl_status.pack(side="right")

        frame_log = tk.Frame(self.root, padx=16, pady=10)
        frame_log.pack(fill="both", expand=True)

        tk.Label(frame_log, text="Log:", font=fonte_normal).pack(anchor="w")

        self.log = scrolledtext.ScrolledText(
            frame_log,
            wrap="word",
            font=("Consolas", 9),
            bg="#1a1a1a",
            fg="#e6e6e6",
            insertbackground="#e6e6e6",
            relief="flat",
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled")

    # ---------------------------------------------------------------- Log
    def _imprimir(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto if texto.endswith("\n") else texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drenar_log(self) -> None:
        try:
            while True:
                linha = self.fila_log.get_nowait()
                self._imprimir(linha)
        except queue.Empty:
            pass
        self.root.after(100, self._drenar_log)

    # ---------------------------------------------------------------- Setup
    def _verificar_arquivos(self) -> None:
        faltando = []
        if not SCRIPT.exists():
            faltando.append(SCRIPT.name)
        if not REQUIREMENTS.exists():
            faltando.append(REQUIREMENTS.name)
        for nome in ("aceitar.png", "selecao_campeoes.png"):
            if not (PASTA_IMAGENS / nome).exists():
                faltando.append(f"imagens/{nome}")
        if faltando:
            self._imprimir(
                "AVISO: arquivos ausentes: " + ", ".join(faltando)
            )
        else:
            self._imprimir("Tudo pronto. Clique em INSTALAR na primeira vez.")

        if self._dependencias_ok():
            self._imprimir("Dependências já instaladas.")
            self.btn_instalar.configure(text="REINSTALAR DEPENDÊNCIAS")

    def _dependencias_ok(self) -> bool:
        for modulo in PACOTES:
            try:
                __import__(modulo)
            except ImportError:
                return False
        return True

    # ---------------------------------------------------------------- Instalar
    def _ao_clicar_instalar(self) -> None:
        self.btn_instalar.configure(state="disabled")
        self.btn_iniciar.configure(state="disabled")
        self._imprimir("Instalando dependências, aguarde...")

        threading.Thread(target=self._rodar_pip, daemon=True).start()

    def _rodar_pip(self) -> None:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "-r",
            str(REQUIREMENTS),
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(PASTA),
                creationflags=_flags_sem_janela(),
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for linha in proc.stdout:
                self.fila_log.put(linha.rstrip())
            codigo = proc.wait()
        except Exception as e:
            self.fila_log.put(f"Erro ao rodar pip: {e}")
            codigo = -1

        if codigo == 0 and self._dependencias_ok():
            self.fila_log.put("Dependências instaladas com sucesso.")
        else:
            self.fila_log.put(
                "Falha ao instalar. Verifique sua conexão e se o Python "
                "está no PATH."
            )

        self.root.after(0, self._reabilitar_apos_instalar)

    def _reabilitar_apos_instalar(self) -> None:
        self.btn_instalar.configure(state="normal", text="REINSTALAR DEPENDÊNCIAS")
        self.btn_iniciar.configure(state="normal")

    # ---------------------------------------------------------------- Iniciar/Parar
    def _ao_clicar_iniciar(self) -> None:
        if self.processo is not None and self.processo.poll() is None:
            return

        if not self._dependencias_ok():
            messagebox.showwarning(
                "Dependências ausentes",
                "Clique em INSTALAR DEPENDÊNCIAS antes de iniciar.",
            )
            return

        if not SCRIPT.exists():
            messagebox.showerror("Erro", f"Arquivo não encontrado: {SCRIPT.name}")
            return

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            self.processo = subprocess.Popen(
                [sys.executable, "-u", str(SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(PASTA),
                creationflags=_flags_sem_janela(),
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as e:
            messagebox.showerror("Erro ao iniciar", str(e))
            return

        self._imprimir("▶ Script iniciado.")
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.lbl_status.configure(text="● Rodando", fg="#2f855a")

        self.thread_leitora = threading.Thread(
            target=self._ler_saida_do_script, daemon=True
        )
        self.thread_leitora.start()

    def _ler_saida_do_script(self) -> None:
        assert self.processo is not None and self.processo.stdout is not None
        for linha in self.processo.stdout:
            self.fila_log.put(linha.rstrip())
        codigo = self.processo.wait()
        self.fila_log.put(f"■ Script encerrado (código {codigo}).")
        self.root.after(0, self._ao_script_encerrar)

    def _ao_script_encerrar(self) -> None:
        self.processo = None
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.lbl_status.configure(text="● Parado", fg="#c53030")

    def _ao_clicar_parar(self) -> None:
        if self.processo is None or self.processo.poll() is not None:
            return
        self._imprimir("Parando script...")
        try:
            self.processo.terminate()
        except Exception as e:
            self._imprimir(f"Erro ao parar: {e}")

    # ---------------------------------------------------------------- Fechar
    def _ao_fechar(self) -> None:
        if self.processo is not None and self.processo.poll() is None:
            if not messagebox.askyesno(
                "Sair",
                "O script ainda está rodando. Deseja parar e sair?",
            ):
                return
            try:
                self.processo.terminate()
                self.processo.wait(timeout=3)
            except Exception:
                try:
                    self.processo.kill()
                except Exception:
                    pass
        self.root.destroy()


def _flags_sem_janela() -> int:
    """No Windows, evita abrir console preto ao rodar subprocessos."""
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return 0


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

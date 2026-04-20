"""
Auto-Aceitar para League of Legends.

Monitora a tela em busca do botão ACEITAR e clica automaticamente.
Encerra ao detectar a tela de Seleção de Campeões.

Uso:
    python auto_aceitar.py

Para parar: Ctrl+C no terminal, ou aguarde entrar na Seleção de Campeões.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np
import pyautogui

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
PASTA_IMAGENS = Path(__file__).parent / "imagens"
IMG_ACEITAR = PASTA_IMAGENS / "aceitar.png"
IMG_SELECAO = PASTA_IMAGENS / "selecao_campeoes.png"

LIMIAR_ACEITAR = 0.80      # 0.0 a 1.0 — quanto maior, mais estrito o match
LIMIAR_SELECAO = 0.80
INTERVALO_LOOP = 0.8       # segundos entre cada checagem (CPU ~0%)
COOLDOWN_POS_CLIQUE = 2.0  # evita cliques múltiplos no mesmo botão

pyautogui.FAILSAFE = False  # parada apenas via Ctrl+C ou Seleção de Campeões
pyautogui.PAUSE = 0.0


@dataclass
class Template:
    """Template de imagem pré-carregado em escala de cinza."""
    nome: str
    imagem: np.ndarray
    largura: int
    altura: int


def carregar_template(caminho: Path, nome: str) -> Template:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Imagem de referência '{nome}' não encontrada em: {caminho}\n"
            f"Veja o README para tirar os prints corretamente."
        )
    img = cv2.imread(str(caminho), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Falha ao decodificar a imagem '{caminho}'.")
    h, w = img.shape[:2]
    return Template(nome=nome, imagem=img, largura=w, altura=h)


def capturar_tela(sct: mss.mss) -> np.ndarray:
    """Captura o monitor primário em escala de cinza (rápido e leve)."""
    monitor = sct.monitors[1]  # monitor 0 = todos os monitores juntos
    raw = np.asarray(sct.grab(monitor))           # BGRA
    cinza = cv2.cvtColor(raw, cv2.COLOR_BGRA2GRAY)
    return cinza


def encontrar_template(
    tela: np.ndarray, template: Template, limiar: float
) -> tuple[int, int] | None:
    """Retorna (x, y) do centro do match, ou None se não encontrar."""
    if tela.shape[0] < template.altura or tela.shape[1] < template.largura:
        return None
    resultado = cv2.matchTemplate(tela, template.imagem, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(resultado)
    if max_val < limiar:
        return None
    centro_x = max_loc[0] + template.largura // 2
    centro_y = max_loc[1] + template.altura // 2
    return centro_x, centro_y


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    log("Iniciando Auto-Aceitar LoL.")
    log("Para parar: Ctrl+C no terminal, ou aguarde entrar na Seleção de Campeões.")

    try:
        tpl_aceitar = carregar_template(IMG_ACEITAR, "ACEITAR")
        tpl_selecao = carregar_template(IMG_SELECAO, "SELEÇÃO DE CAMPEÕES")
    except (FileNotFoundError, ValueError) as e:
        log(f"ERRO: {e}")
        return 1

    log("Templates carregados. Procurando partida...")

    ultimo_clique = 0.0

    with mss.mss() as sct:
        while True:
            try:
                tela = capturar_tela(sct)
            except Exception as e:
                # Cliente minimizado, troca de monitor, screen lock, etc.
                log(f"Aviso: falha ao capturar tela ({e}). Tentando novamente...")
                time.sleep(1.5)
                continue

            # 1) Já entrou na seleção de campeões? Encerrar.
            if encontrar_template(tela, tpl_selecao, LIMIAR_SELECAO):
                log("Entrou na Seleção de Campeões. Encerrando...")
                return 0

            # 2) Botão ACEITAR visível? Clicar.
            agora = time.time()
            if agora - ultimo_clique > COOLDOWN_POS_CLIQUE:
                pos = encontrar_template(tela, tpl_aceitar, LIMIAR_ACEITAR)
                if pos is not None:
                    x, y = pos
                    log(f"Partida encontrada! Clicando em ({x}, {y})...")
                    pyautogui.click(x, y)
                    ultimo_clique = agora
                    log("Clique enviado. Aguardando confirmação da partida...")

            time.sleep(INTERVALO_LOOP)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Interrompido pelo usuário (Ctrl+C). Encerrando.")
        sys.exit(0)

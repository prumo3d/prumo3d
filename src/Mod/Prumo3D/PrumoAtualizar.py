# SPDX-License-Identifier: LGPL-2.1-or-later
"""Atualização do Prumo 3D pela página de versões do GitHub (nunca obrigatória).

- Ajuda → Sobre: botão "Verificar atualizações" e a chave "Verificar ao abrir".
- Ao abrir (no máximo uma vez por dia, desligável): se houver versão mais nova, aparece um aviso com
  "Atualizar agora", "Agora não" e "Pular esta versão". Nada acontece sem o usuário concordar.
- Atualizar agora:
  - Windows instalado: baixa o instalador, confere o SHA-256 publicado, pede para fechar o Prumo
    (o FreeCAD pergunta se quer salvar o que estiver aberto) e abre o instalador;
  - Linux (AppImage): baixa o AppImage novo na mesma pasta do atual e diz onde ficou;
  - outros casos (pasta portátil, compilação própria): abre a página da versão no navegador.

A consulta só lê a lista de versões públicas do projeto; nenhum dado do usuário é enviado.
"""

import hashlib
import json
import os
import sys
import tempfile
import threading
import time

import FreeCAD

REPO = "prumo3d/prumo3d"
API = "https://api.github.com/repos/{}/releases?per_page=10".format(REPO)
PAGINA = "https://github.com/{}/releases".format(REPO)
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
INTERVALO = 24 * 3600        # verificação automática: no máximo uma vez por dia


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


# ----------------------------------------------------------------------------------- versões
def versao_atual():
    import PrumoVersao
    return ("%s-%s" % (PrumoVersao.VERSAO, PrumoVersao.CANAL)).rstrip("-")


def compilada():
    """True numa versão gerada pelo fluxo de publicação (só nela a comparação faz sentido)."""
    try:
        from PrumoVersaoCompilada import VERSAO_COMPILADA
        return bool(VERSAO_COMPILADA)
    except Exception:
        return False


def chave(rotulo):
    """'0.6.0-beta' -> ((0, 6, 0), 0, 'beta'); a versão final vem depois da beta do mesmo número."""
    import PrumoVersao
    v, canal = PrumoVersao.separar(rotulo)
    nums = []
    for p in v.split("."):
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums), (0 if canal else 1), canal


def mais_nova(a, b):
    """a é mais nova que b?"""
    return chave(a) > chave(b)


# ----------------------------------------------------------------------------------- consulta
def escolher(releases, aceitar_beta=True):
    """A versão mais nova da lista da API (sem rascunhos; betas só se aceitas)."""
    melhor = None
    for r in releases or []:
        if r.get("draft"):
            continue
        if r.get("prerelease") and not aceitar_beta:
            continue
        tag = r.get("tag_name") or ""
        if not tag:
            continue
        if melhor is None or mais_nova(tag, melhor["tag_name"]):
            melhor = r
    if melhor is None:
        return None
    import PrumoVersao
    v, canal = PrumoVersao.separar(melhor["tag_name"])
    return {
        "tag": melhor["tag_name"],
        "versao": ("%s-%s" % (v, canal)).rstrip("-"),
        "texto": ("%s %s" % (v, canal)).strip(),
        "pagina": melhor.get("html_url") or PAGINA,
        "notas": melhor.get("body") or "",
        "ativos": [{"nome": a.get("name", ""), "tamanho": int(a.get("size") or 0),
                    "url": a.get("browser_download_url", ""), "digest": a.get("digest") or ""}
                   for a in melhor.get("assets", [])],
    }


def _abrir_url(url, timeout, aceitar="application/vnd.github+json"):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Prumo3D/" + versao_atual(),
                                               "Accept": aceitar})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except Exception as exc:
        # sem certificados do sistema (algumas instalações): tenta os do certifi, se houver
        if "CERTIFICATE" not in str(exc).upper():
            raise
        import ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def consultar(timeout=8, aceitar_beta=None):
    """Lê a página de versões. Devolve o dicionário da versão mais nova ou lança a exceção."""
    if aceitar_beta is None:
        aceitar_beta = _params().GetBool("AtualizarBetas", True)
    with _abrir_url(API, timeout) as r:
        dados = json.loads(r.read().decode("utf-8"))
    return escolher(dados, aceitar_beta)


def tem_novidade(info, atual=None):
    return info is not None and mais_nova(info["versao"], atual or versao_atual())


# ----------------------------------------------------------------------------------- instalação
def modo_instalacao():
    """'instalador' (Windows instalado), 'appimage' (Linux) ou 'manual'."""
    if sys.platform.startswith("win"):
        try:
            casa = FreeCAD.getHomePath()
            if any(n.lower().startswith("uninstall") and n.lower().endswith(".exe")
                   for n in os.listdir(casa)):
                return "instalador"
        except Exception:
            pass
        return "manual"
    if os.environ.get("APPIMAGE"):
        return "appimage"
    return "manual"


def ativo_do_sistema(info, modo=None):
    modo = modo or modo_instalacao()
    fim = {"instalador": "-installer.exe", "appimage": ".AppImage"}.get(modo)
    if not fim or info is None:
        return None
    for a in info["ativos"]:
        if a["nome"].endswith(fim):
            return a
    return None


def baixar(url, destino, digest="", progresso=None, cancelado=None, timeout=30):
    """Baixa em partes para destino (arquivo .parte até terminar) e confere o SHA-256 quando há.

    progresso(feito, total) é chamado a cada parte; cancelado() True interrompe. Devolve destino.
    """
    parte = destino + ".parte"
    h = hashlib.sha256()
    feito = 0
    with _abrir_url(url, timeout, aceitar="application/octet-stream") as r:
        total = int(r.headers.get("Content-Length") or 0)
        with open(parte, "wb") as f:
            while True:
                if cancelado is not None and cancelado():
                    raise InterruptedError("download cancelado")
                bloco = r.read(1024 * 256)
                if not bloco:
                    break
                f.write(bloco)
                h.update(bloco)
                feito += len(bloco)
                if progresso is not None:
                    progresso(feito, total)
    if digest.startswith("sha256:") and h.hexdigest().lower() != digest.split(":", 1)[1].lower():
        os.remove(parte)
        raise ValueError("o arquivo baixado não confere com o publicado (SHA-256 diferente)")
    if os.path.exists(destino):
        os.remove(destino)
    os.replace(parte, destino)
    return destino


def pasta_download():
    p = os.path.join(tempfile.gettempdir(), "Prumo3D-atualizacao")
    os.makedirs(p, exist_ok=True)
    return p


# ----------------------------------------------------------------------------------- interface
def _qt():
    from PySide import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def _resumo_notas(md, limite=1400):
    """Só a parte "Novidades" das notas, em texto simples."""
    linhas = []
    for ln in (md or "").splitlines():
        s = ln.strip()
        if s.startswith("## ") and linhas:
            break
        if s.startswith("#"):
            continue
        linhas.append(ln)
    txt = "\n".join(linhas).strip()
    return txt if len(txt) <= limite else txt[:limite].rsplit("\n", 1)[0] + "\n…"


def janela_principal():
    try:
        import FreeCADGui
        return FreeCADGui.getMainWindow()
    except Exception:
        return None


class AvisoAtualizacao:
    """Janela "Prumo 3D X disponível". Nunca atualiza sem o clique em "Atualizar agora"."""

    def __init__(self, info, automatico=False, parent=None):
        QtCore, QtGui, QtWidgets = _qt()
        import PrumoUI as UI
        self.info = info
        self.d = QtWidgets.QDialog(parent or janela_principal())
        d = self.d
        d.setObjectName("PrumoUI")
        d.setWindowTitle("Atualização do Prumo 3D")
        d.setStyleSheet(UI.qss())
        d.setMinimumWidth(460)
        v = QtWidgets.QVBoxLayout(d)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)
        t = QtWidgets.QLabel("Prumo 3D {} disponível".format(info["texto"]))
        t.setStyleSheet(UI.tema("color: #003A70; font-size: 13pt; font-weight: 700;"))
        v.addWidget(t)
        sub = QtWidgets.QLabel("Você está usando a versão {}. A atualização é opcional.".format(
            versao_atual().replace("-", " ")))
        sub.setObjectName("PrumoSub")
        v.addWidget(sub)
        notas = QtWidgets.QTextBrowser()
        notas.setOpenExternalLinks(True)
        notas.setMarkdown(_resumo_notas(info["notas"]) or "Veja as novidades na página da versão.")
        notas.setMinimumHeight(180)
        v.addWidget(notas, 1)
        self.modo = modo_instalacao()
        self.ativo = ativo_do_sistema(info, self.modo)
        explica = {
            "instalador": "Ao atualizar, o Prumo baixa o instalador ({}), fecha (perguntando se quer salvar o "
                          "que estiver aberto) e abre o instalador.",
            "appimage": "Ao atualizar, o Prumo baixa o arquivo novo ({}) para a mesma pasta do atual.",
        }.get(self.modo, "Esta instalação não se atualiza sozinha: \"Atualizar agora\" abre a página da versão "
                         "para baixar.")
        tam = "{:.0f} MB".format(self.ativo["tamanho"] / 1e6) if self.ativo else ""
        ex = QtWidgets.QLabel(explica.format(tam))
        ex.setObjectName("PrumoSub")
        ex.setWordWrap(True)
        v.addWidget(ex)
        bb = QtWidgets.QHBoxLayout()
        self.pular = None
        if automatico:
            self.pular = QtWidgets.QPushButton("Pular esta versão")
            self.pular.clicked.connect(self._pular)
            bb.addWidget(self.pular)
        bb.addStretch(1)
        self.depois = QtWidgets.QPushButton("Agora não")
        self.depois.clicked.connect(d.reject)
        bb.addWidget(self.depois)
        self.atualizar = QtWidgets.QPushButton("Atualizar agora")
        self.atualizar.setObjectName("PrumoPrimario")
        self.atualizar.setDefault(True)
        self.atualizar.clicked.connect(self._atualizar)
        bb.addWidget(self.atualizar)
        v.addLayout(bb)
        # o Python precisa segurar este objeto enquanto a janela estiver aberta: sem isso ele some da
        # memória e os botões ligados aos métodos dele (Atualizar agora) deixam de responder
        _vivos.append(self)
        d.finished.connect(lambda _r: self in _vivos and _vivos.remove(self))

    def mostrar(self):
        self.d.show()
        self.d.raise_()
        return self

    def _pular(self):
        _params().SetString("PularVersao", self.info["tag"])
        self.d.reject()

    def _atualizar(self):
        pai = self.d.parentWidget()
        self.d.accept()
        atualizar(self.info, self.modo, self.ativo, parent=pai)


def atualizar(info, modo=None, ativo=None, parent=None):
    QtCore, QtGui, QtWidgets = _qt()
    modo = modo or modo_instalacao()
    ativo = ativo or ativo_do_sistema(info, modo)
    if modo == "manual" or ativo is None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(info["pagina"]))
        QtWidgets.QMessageBox.information(
            parent or _pai_para_janela(), "Atualização do Prumo 3D",
            "Esta instalação não se atualiza sozinha. A página da versão {} foi aberta no navegador: baixe "
            "o arquivo do seu sistema por lá.".format(info["texto"]))
        return "pagina"
    if modo == "appimage":
        pasta = os.path.dirname(os.environ.get("APPIMAGE", "")) or os.path.expanduser("~")
    else:
        pasta = pasta_download()
    destino = os.path.join(pasta, ativo["nome"])
    JanelaDownload(ativo, destino, modo, info.get("texto", ""), parent=parent).iniciar()
    return "baixando"


def _pai_para_janela():
    """Janela modal aberta (ex.: Sobre) ou a principal: uma janela filha da principal ficaria travada
    atrás de um diálogo modal."""
    QtCore, QtGui, QtWidgets = _qt()
    return QtWidgets.QApplication.activeModalWidget() or janela_principal()


def _mb(n):
    return "{:.1f}".format(n / 1e6).replace(".", ",")


def _tempo(seg):
    seg = int(max(0, seg))
    if seg < 60:
        return "menos de 1 min"
    return "cerca de {} min".format(int(round(seg / 60.0)))


class JanelaDownload:
    """Janela de atualização no padrão do Prumo: barra de progresso, MB, velocidade, tempo que falta e
    Cancelar; no fim, o próximo passo (instalar agora ou onde ficou o arquivo) ou o erro, na mesma janela."""

    def __init__(self, ativo, destino, modo, texto_versao="", parent=None):
        QtCore, QtGui, QtWidgets = _qt()
        import PrumoUI as UI
        self.ativo, self.destino, self.modo = ativo, destino, modo
        self.estado = {"feito": 0, "total": ativo.get("tamanho", 0), "erro": None, "fim": False, "cancelar": False}
        self.inicio = None
        self.d = QtWidgets.QDialog(parent or _pai_para_janela())
        d = self.d
        d.setObjectName("PrumoUI")
        d.setWindowTitle("Atualização do Prumo 3D")
        d.setStyleSheet(UI.qss() + UI.tema(
            "QProgressBar { border: 1px solid #DCE4EC; border-radius: 6px; background: #EEF2F6; height: 14px;"
            " text-align: center; color: transparent; }"
            "QProgressBar::chunk { background: #003A70; border-radius: 6px; }"
            "QLabel#PrumoErro { color: #A33A2B; font-weight: 600; }"
            "QLabel#PrumoOk { color: #1E7A4C; font-weight: 600; }"))
        d.setMinimumWidth(480)
        v = QtWidgets.QVBoxLayout(d)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)
        self.texto_versao = texto_versao
        self.titulo = QtWidgets.QLabel("Baixando o Prumo 3D {}".format(texto_versao).strip())
        self.titulo.setStyleSheet(UI.tema("color: #003A70; font-size: 13pt; font-weight: 700;"))
        v.addWidget(self.titulo)
        self.situacao = QtWidgets.QLabel("Preparando o download…")
        self.situacao.setWordWrap(True)
        v.addWidget(self.situacao)
        self.barra = QtWidgets.QProgressBar()
        self.barra.setRange(0, 0)          # até saber o tamanho: barra "andando"
        self.barra.setTextVisible(False)
        v.addWidget(self.barra)
        self.detalhe = QtWidgets.QLabel(ativo.get("nome", ""))
        self.detalhe.setObjectName("PrumoSub")
        self.detalhe.setWordWrap(True)
        v.addWidget(self.detalhe)
        bb = QtWidgets.QHBoxLayout()
        bb.addStretch(1)
        self.secundario = QtWidgets.QPushButton("Cancelar")
        self.secundario.setAutoDefault(False)
        self.secundario.setDefault(False)
        self.secundario.clicked.connect(self._cancelar)
        bb.addWidget(self.secundario)
        self.principal = QtWidgets.QPushButton("")
        self.principal.setObjectName("PrumoPrimario")
        self.principal.setAutoDefault(False)
        self.principal.setVisible(False)
        self.principal.clicked.connect(self._principal)
        bb.addWidget(self.principal)
        v.addLayout(bb)
        self.acao = None
        d.rejected.connect(self._fechou)
        self.t = QtCore.QTimer()
        self.t.setInterval(200)
        self.t.timeout.connect(self._tick)

    # ---------------------------------------------------------------- download em segundo plano
    def _trabalho(self):
        try:
            baixar(self.ativo["url"], self.destino, self.ativo.get("digest", ""),
                   progresso=lambda f, t: self.estado.update(feito=f, total=t or self.estado["total"]),
                   cancelado=lambda: self.estado["cancelar"])
        except Exception as exc:
            self.estado["erro"] = exc
        self.estado["fim"] = True

    def iniciar(self):
        self.inicio = time.time()
        self.estado.update(feito=0, erro=None, fim=False, cancelar=False)
        threading.Thread(target=self._trabalho, daemon=True).start()
        self.t.start()
        if self not in _vivos:
            _vivos.append(self)
        self.d.show()
        self.d.raise_()
        self.d.activateWindow()
        return self

    def _tick(self):
        e = self.estado
        if e["total"] and e["feito"]:
            frac = min(1.0, e["feito"] / float(e["total"]))
            if self.barra.maximum() == 0:
                self.barra.setRange(0, 1000)
            self.barra.setValue(int(1000 * frac))
            dt = max(0.001, time.time() - (self.inicio or time.time()))
            vel = e["feito"] / dt
            falta = (e["total"] - e["feito"]) / vel if vel > 0 else 0
            self.situacao.setText("Baixando… {:.0f}%".format(100 * frac))
            self.detalhe.setText("{} de {} MB · {} MB/s · falta {}".format(
                _mb(e["feito"]), _mb(e["total"]), _mb(vel), _tempo(falta)))
        elif e["feito"]:
            self.situacao.setText("Baixando… {} MB".format(_mb(e["feito"])))
        if not e["fim"]:
            return
        self.t.stop()
        if e["erro"] is not None:
            if isinstance(e["erro"], InterruptedError):
                self._fim_do_objeto()
                self.d.close()
                return
            self._erro(e["erro"])
            return
        self._pronto()

    # ---------------------------------------------------------------- estados finais
    def _erro(self, exc):
        self.barra.setRange(0, 1000)
        self.barra.setValue(0)
        self.situacao.setObjectName("PrumoErro")
        self.situacao.style().unpolish(self.situacao)
        self.situacao.style().polish(self.situacao)
        self.situacao.setText("Não foi possível baixar a atualização.")
        self.detalhe.setText("{}\n\nVerifique a internet e tente de novo, ou baixe pela página de versões:\n{}"
                             .format(exc, PAGINA))
        self.acao = "tentar"
        self.principal.setText("Tentar de novo")
        self.principal.setVisible(True)
        self.secundario.setText("Fechar")
        self._ajustar()

    def _pronto(self):
        self.barra.setRange(0, 1000)
        self.barra.setValue(1000)
        self.situacao.setObjectName("PrumoOk")
        self.situacao.style().unpolish(self.situacao)
        self.situacao.style().polish(self.situacao)
        if self.modo == "appimage":
            try:
                os.chmod(self.destino, 0o755)
            except OSError:
                pass
            self.situacao.setText("Pronto: a versão nova foi baixada e conferida.")
            self.titulo.setText("Prumo 3D {} baixado".format(self.texto_versao).replace("  ", " "))
            self.detalhe.setText("Arquivo: {}\nPasta: {}\n\nFeche o Prumo e abra esse arquivo. O arquivo antigo "
                                 "pode ser apagado depois.".format(os.path.basename(self.destino),
                                                                   os.path.dirname(self.destino)))
            self.acao = None
            self.principal.setVisible(False)
            self.secundario.setText("Fechar")
            self._ajustar()
            return
        self.situacao.setText("Pronto: o instalador foi baixado e conferido.")
        self.titulo.setText("Prumo 3D {} pronto para instalar".format(self.texto_versao).replace("  ", " "))
        self.detalhe.setText("Para instalar, o Prumo precisa fechar (ele pergunta se quer salvar o que estiver "
                             "aberto).\n\nSe preferir depois, o instalador fica na pasta:\n{}".format(
                                 os.path.dirname(self.destino)))
        self.acao = "instalar"
        self.principal.setText("Fechar o Prumo e instalar")
        self.principal.setVisible(True)
        self.secundario.setText("Depois")
        self._ajustar()

    def _ajustar(self):
        """Texto com quebra de linha não faz a janela crescer sozinha: calcula a altura e reajusta."""
        QtCore, QtGui, QtWidgets = _qt()
        for lb in (self.situacao, self.detalhe):
            w = max(lb.width(), self.d.width() - 36)
            lb.setMinimumHeight(lb.heightForWidth(w) if lb.hasHeightForWidth() else lb.sizeHint().height())
        self.d.adjustSize()

    # ---------------------------------------------------------------- botões
    def _principal(self):
        if self.acao == "tentar":
            self.situacao.setObjectName("")
            self.situacao.style().unpolish(self.situacao)
            self.situacao.style().polish(self.situacao)
            self.situacao.setText("Preparando o download…")
            self.detalhe.setText(self.ativo.get("nome", ""))
            self.barra.setRange(0, 0)
            self.principal.setVisible(False)
            self.secundario.setText("Cancelar")
            self.iniciar()
        elif self.acao == "instalar":
            self.d.accept()
            self._fim_do_objeto()
            instalar_ao_fechar(self.destino)

    def _cancelar(self):
        if not self.estado["fim"]:
            self.estado["cancelar"] = True
            self.situacao.setText("Cancelando…")
            self.secundario.setEnabled(False)
            return
        self.d.reject()

    def _fechou(self):
        if not self.estado["fim"]:
            self.estado["cancelar"] = True      # fechou a janela no X durante o download
        self._fim_do_objeto()

    def _fim_do_objeto(self):
        if self.estado["fim"] and self in _vivos:
            _vivos.remove(self)


Baixador = JanelaDownload      # nome antigo


_vivos = []


def instalar_ao_fechar(caminho):
    """Abre o instalador quando o Prumo terminar de fechar (se o usuário cancelar o fechamento, nada)."""
    QtCore, QtGui, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()

    def abrir():
        import subprocess
        try:
            subprocess.Popen([caminho], close_fds=True,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        except Exception as exc:
            FreeCAD.Console.PrintError("Prumo: não abriu o instalador: {}\n".format(exc))

    app.aboutToQuit.connect(abrir)
    mw = janela_principal()
    if mw is not None and not mw.close():
        # fechamento cancelado (ex.: o usuário desistiu na pergunta de salvar)
        try:
            app.aboutToQuit.disconnect(abrir)
        except Exception:
            pass
        return False
    return True


# ----------------------------------------------------------------------------------- verificação
class Verificacao:
    """Consulta em segundo plano; ao_terminar(info, erro) roda na interface."""

    def __init__(self, ao_terminar):
        QtCore, QtGui, QtWidgets = _qt()
        self.ao_terminar = ao_terminar
        self.res = {"fim": False, "info": None, "erro": None}
        self.t = QtCore.QTimer()
        self.t.setInterval(250)
        self.t.timeout.connect(self._tick)

    def _trabalho(self):
        try:
            self.res["info"] = consultar()
        except Exception as exc:
            self.res["erro"] = exc
        self.res["fim"] = True

    def iniciar(self):
        threading.Thread(target=self._trabalho, daemon=True).start()
        self.t.start()
        _vivos.append(self)
        return self

    def _tick(self):
        if not self.res["fim"]:
            return
        self.t.stop()
        if self in _vivos:
            _vivos.remove(self)
        try:
            self.ao_terminar(self.res["info"], self.res["erro"])
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: atualização: {}\n".format(exc))


def verificar_agora(parent=None):
    """Botão "Verificar atualizações" (Sobre): sempre mostra o resultado (e "Procurando…" enquanto isso)."""
    QtCore, QtGui, QtWidgets = _qt()
    espera = QtWidgets.QProgressDialog("Procurando atualizações…", None, 0, 0, parent or _pai_para_janela())
    espera.setWindowTitle("Atualização do Prumo 3D")
    espera.setMinimumDuration(0)
    espera.setCancelButton(None)
    espera.show()

    def fim(info, erro):
        espera.close()
        _params().SetFloat("UltimaVerificacao", time.time())
        if erro is not None:
            QtWidgets.QMessageBox.information(
                parent or janela_principal(), "Atualização do Prumo 3D",
                "Não foi possível consultar a página de versões (sem internet ou bloqueado pela rede).\n\n"
                "Endereço: {}".format(PAGINA))
            return
        if tem_novidade(info):
            AvisoAtualizacao(info, automatico=False, parent=parent).mostrar()
        else:
            QtWidgets.QMessageBox.information(parent or janela_principal(), "Atualização do Prumo 3D",
                                              "Você já está com a versão mais nova ({}).".format(
                                                  versao_atual().replace("-", " ")))

    return Verificacao(fim).iniciar()


def deve_verificar_ao_abrir(agora=None):
    p = _params()
    if not p.GetBool("VerificarAtualizacoes", True) or not compilada():
        return False
    agora = agora or time.time()
    return agora - p.GetFloat("UltimaVerificacao", 0.0) >= INTERVALO


def verificar_ao_abrir():
    """Chamado alguns segundos depois de abrir. Silencioso se não houver novidade ou sem internet."""
    if not deve_verificar_ao_abrir():
        return None

    def fim(info, erro):
        _params().SetFloat("UltimaVerificacao", time.time())
        if erro is not None or not tem_novidade(info):
            return
        if info["tag"] == _params().GetString("PularVersao", ""):
            return
        _estado["aviso"] = AvisoAtualizacao(info, automatico=True).mostrar()

    return Verificacao(fim).iniciar()


_estado = {"aviso": None}

# SPDX-License-Identifier: LGPL-2.1-or-later
"""Vídeo do comportamento da estrutura (análise por barras) e do detalhe por elementos finitos.

Cada quadro é uma captura da vista 3D com uma faixa de título e uma legenda desenhadas por cima
(Pillow). O vídeo sai em MP4 quando o ffmpeg está disponível (vem no pacote do Prumo) e em GIF
animado como alternativa.
"""
import math
import os
import shutil
import subprocess
import tempfile

import FreeCAD
import FreeCADGui

HERE = os.path.dirname(os.path.abspath(__file__))
AZUL = (0, 58, 112)
AMARELO = (247, 190, 0)
BRANCO = (255, 255, 255)
CINZA = (91, 104, 118)
CORES_TAXA = [((38, 166, 77), "até 0,70"), ((242, 204, 26), "0,70 a 0,90"), ((242, 115, 13), "0,90 a 1,00"),
              ((217, 26, 26), "acima de 1,00")]


# ------------------------------------------------------------------ utilidades
def ffmpeg():
    """Caminho do ffmpeg (o do Prumo, o do sistema) ou None."""
    home = FreeCAD.getHomePath()
    for pasta in (os.path.join(home, "bin"), os.path.join(home, "Library", "bin"), home):
        for nome in ("ffmpeg.exe", "ffmpeg"):
            c = os.path.join(pasta, nome)
            if os.path.isfile(c):
                return c
    return shutil.which("ffmpeg")


def _fonte(tamanho, peso="SemiBold", texto=""):
    from PIL import ImageFont
    if any(ord(c) > 0x24F for c in texto):     # σ, γ, Δ: a Poppins não tem letras gregas
        try:
            import matplotlib
            nome = "DejaVuSans-Bold.ttf" if peso in ("SemiBold", "Bold") else "DejaVuSans.ttf"
            c = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", nome)
            return ImageFont.truetype(c, tamanho)
        except Exception:
            pass
    for nome in ("Poppins-%s.ttf" % peso, "Poppins-Regular.ttf"):
        c = os.path.join(HERE, "Resources", "fonts", nome)
        if os.path.isfile(c):
            return ImageFont.truetype(c, tamanho)
    try:
        import matplotlib
        c = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")
        return ImageFont.truetype(c, tamanho)
    except Exception:
        return ImageFont.load_default()


def _f(v, casas=2):
    return ("%." + str(casas) + "f") % v if v is not None else "—"


def _br(v, casas=2):
    return _f(v, casas).replace(".", ",")


class Gravador:
    """Junta quadros (PNG) com faixa de título e legenda e grava MP4 ou GIF."""

    def __init__(self, largura=1280, altura=720, fps=24):
        self.w, self.h, self.fps = int(largura), int(altura), int(fps)
        self.pasta = tempfile.mkdtemp(prefix="prumo_video_")
        self.n = 0
        self.titulo = ""
        self.subtitulo = ""
        self.legenda = []        # [(cor RGB, texto)]
        self.rodape = ""

    def quadro(self, vezes=1):
        """Captura a vista 3D atual e grava `vezes` cópias (para segurar a cena)."""
        from PIL import Image
        FreeCADGui.updateGui()
        v = FreeCADGui.ActiveDocument.ActiveView
        bruto = os.path.join(self.pasta, "_bruto.png")
        v.saveImage(bruto, self.w, self.h, "White")
        img = Image.open(bruto).convert("RGB")
        img = self._decorar(img)
        for _k in range(max(1, int(vezes))):
            img.save(os.path.join(self.pasta, "q%05d.png" % self.n))
            self.n += 1

    def _decorar(self, img):
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        w, h = img.size
        faixa = int(h * 0.11)
        d.rectangle([0, 0, w, faixa], fill=AZUL)
        d.rectangle([0, faixa, w, faixa + max(3, h // 180)], fill=AMARELO)
        ft = _fonte(int(faixa * 0.36), "SemiBold", self.titulo)
        fs = _fonte(int(faixa * 0.22), "Regular", self.subtitulo)
        d.text((int(w * 0.025), int(faixa * 0.14)), self.titulo, font=ft, fill=BRANCO)
        if self.subtitulo:
            d.text((int(w * 0.025), int(faixa * 0.62)), self.subtitulo, font=fs, fill=(220, 228, 236))
        tam_l = max(12, int(h * 0.024))

        def fl_de(txt):
            return _fonte(tam_l, "Regular", txt)
        fl = fl_de("")
        if self.legenda:
            lado = int(h * 0.028)
            y = h - int(h * 0.06) - len(self.legenda) * int(lado * 1.4)
            x = int(w * 0.025)
            for cor, txt in self.legenda:
                d.rectangle([x, y, x + lado, y + lado], fill=cor, outline=(60, 60, 60))
                d.text((x + int(lado * 1.4), y - 2), txt, font=fl_de(txt), fill=(30, 42, 54))
                y += int(lado * 1.4)
        if self.rodape:
            d.text((int(w * 0.025), h - int(h * 0.045)), self.rodape, font=fl_de(self.rodape), fill=CINZA)
        marca = "Prumo 3D"
        d.text((w - int(w * 0.12), h - int(h * 0.045)), marca, font=fl, fill=AZUL)
        return img

    def gravar(self, caminho):
        """Grava o vídeo. Retorna o caminho gravado (a extensão pode mudar para .gif sem ffmpeg)."""
        if self.n == 0:
            raise ValueError("nenhum quadro gravado")
        base, ext = os.path.splitext(caminho)
        ext = ext.lower()
        exe = ffmpeg()
        if ext != ".gif" and exe:
            saida = base + ".mp4"
            cmd = [exe, "-y", "-loglevel", "error", "-framerate", str(self.fps),
                   "-i", os.path.join(self.pasta, "q%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", saida]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
                self.limpar()
                return saida
            except Exception as ex:
                FreeCAD.Console.PrintWarning("Prumo: ffmpeg falhou (%s); gravando GIF.\n" % ex)
        saida = base + ".gif"
        self._gif(saida)
        self.limpar()
        return saida

    def _gif(self, saida, fps_gif=12, largura_max=960):
        from PIL import Image
        passo = max(1, int(round(self.fps / float(fps_gif))))
        quadros = []
        for k in range(0, self.n, passo):
            im = Image.open(os.path.join(self.pasta, "q%05d.png" % k))
            if im.width > largura_max:
                im = im.resize((largura_max, int(im.height * largura_max / im.width)))
            quadros.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
        quadros[0].save(saida, save_all=True, append_images=quadros[1:], loop=0,
                        duration=int(1000 * passo / self.fps), optimize=True)

    def limpar(self):
        shutil.rmtree(self.pasta, ignore_errors=True)


def _balancar(v, k, n, amplitude=25.0, ciclos=1.0):
    """Câmera balançando de um lado para o outro (sem chegar a ver a estrutura de lado)."""
    a0 = amplitude * math.sin(2 * math.pi * ciclos * (k - 1) / float(n)) if k > 0 else 0.0
    a1 = amplitude * math.sin(2 * math.pi * ciclos * k / float(n))
    _girar(v, a1 - a0)


def _vista_inicial(v, est):
    """De frente para o plano do esqueleto, um pouco de cima e de lado (estruturas planas)."""
    from pivy import coin
    try:
        import PrumoEstrutura as E
        n = E._normal_esqueleto(E.arestas(est.Esqueleto))
    except Exception:
        n = None
    if n is None or n.Length < 1e-9 or abs(n.z) > 0.9:
        v.viewIsometric()
    else:
        n = FreeCAD.Vector(n).normalize()
        if n.y > 0 or (abs(n.y) < 1e-9 and n.x > 0):
            n = -n
        olho = FreeCAD.Vector(n.x, n.y, 0).normalize() + FreeCAD.Vector(0, 0, 0.45)
        # alinha o "para cima" da câmera com +Z
        cam = v.getCameraNode()
        alvo = FreeCAD.Vector(0, 0, 0) - olho
        z = -alvo.normalize()
        x = FreeCAD.Vector(0, 0, 1).cross(z)
        if x.Length < 1e-9:
            x = FreeCAD.Vector(1, 0, 0)
        x.normalize()
        y = z.cross(x)
        m = FreeCAD.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)
        q = FreeCAD.Rotation(m).Q
        cam.orientation.setValue(coin.SbRotation(q[0], q[1], q[2], q[3]))
    v.fitAll()


def _girar(v, graus):
    """Gira a câmera em torno do eixo vertical (Z) passando pelo centro da cena."""
    from pivy import coin
    cam = v.getCameraNode()
    rot = coin.SbRotation(coin.SbVec3f(0, 0, 1), math.radians(graus))
    centro = cam.position.getValue() + cam.orientation.getValue().multVec(coin.SbVec3f(0, 0, -1)) * \
        cam.focalDistance.getValue()
    pos = cam.position.getValue() - centro
    pos = rot.multVec(pos)
    cam.position.setValue(centro + pos)
    cam.orientation.setValue(cam.orientation.getValue() * rot)


# ------------------------------------------------------------------ estrutura (barras)
def gravar_estrutura(analise, caminho, largura=1280, altura=720, fps=24, segundos=16.0, progresso=None):
    """Vídeo da análise por barras: cargas e apoios, deformada com a taxa de uso (pulsando),
    momento fletor e a taxa de uso com as barras críticas. Retorna o arquivo gravado."""
    import PrumoAnaliseEstrutura as A
    obj = analise
    calc = getattr(obj.Proxy, "calc", None) or obj.Proxy.calcular_silencioso(obj)
    if calc is None or calc.erro or not calc.resultados:
        raise ValueError("calcule a estrutura antes de gravar o vídeo")
    doc = obj.Document
    v = FreeCADGui.ActiveDocument.ActiveView
    estado = (obj.Mostrar, obj.Escala, obj.Combinacao)
    est = obj.Estrutura
    transp = None
    try:
        transp = est.ViewObject.Transparency
    except Exception:
        pass
    gr = Gravador(largura, altura, fps)
    nome_est = est.Label
    piores = sorted(calc.verificacao.items(), key=lambda kv: -kv[1]["taxa"])
    pior_txt = ""
    if piores:
        i, vv = piores[0]
        pior_txt = "Barra %d (%s): taxa %s · %s" % (i + 1, calc.mapa["secoes"][i]["nome"], _br(vv["taxa"]),
                                                    vv["governa"])
    import PrumoAnaliseVista as V
    comb = V._pior_combinacao(calc)
    n_cena = max(2, int(segundos * fps / 4))
    try:
        try:
            est.ViewObject.Transparency = 70
        except Exception:
            pass
        import PrumoAnaliseVista as V
        V.OPCOES["sem_titulo"] = True
        # 1 cargas e apoios
        obj.Mostrar = "Cargas e apoios"
        obj.Combinacao = ""
        doc.recompute()
        _vista_inicial(v, est)
        gr.titulo = "%s · cargas e apoios" % nome_est
        gr.subtitulo = "%d casos de carga · %d combinações (NBR 8681)" % (len(obj.Proxy.casos(obj)),
                                                                          len(calc.combinacoes))
        gr.legenda, gr.rodape = [], "Análise por barras · pórtico espacial"
        for k in range(n_cena):
            _balancar(v, k, n_cena)
            gr.quadro()
            if progresso:
                progresso(gr.n)
        # 2 deformada com a taxa de uso, pulsando
        obj.Mostrar = A.DEFORMADA_TAXA
        obj.Combinacao = comb
        gr.titulo = "%s · como a estrutura se deforma" % nome_est
        gr.subtitulo = "%s · deslocamentos exagerados para ver o movimento" % comb
        gr.legenda = [(c, "taxa de uso " + t) for c, t in CORES_TAXA]
        gr.rodape = "Maior deslocamento (ELS): %s mm" % _br(obj.DeslocamentoMax, 1)
        for k in range(n_cena):
            obj.Escala = 0.05 + 1.95 * (0.5 - 0.5 * math.cos(2 * math.pi * 2 * k / n_cena))
            doc.recompute()
            _balancar(v, k, n_cena)
            gr.quadro()
            if progresso:
                progresso(gr.n)
        # 3 momento fletor crescendo
        obj.Mostrar = "Momento fletor (M)"
        gr.titulo = "%s · momento fletor" % nome_est
        gr.subtitulo = comb
        gr.legenda, gr.rodape = [], "Diagrama de momento fletor na combinação que governa"
        for k in range(n_cena):
            obj.Escala = max(0.02, min(1.0, 1.5 * k / n_cena))
            doc.recompute()
            _balancar(v, k, n_cena, 15.0)
            gr.quadro()
            if progresso:
                progresso(gr.n)
        # 4 taxa de uso: zonas críticas
        obj.Mostrar = "Taxa de uso"
        obj.Escala = 1.0
        doc.recompute()
        gr.titulo = "%s · zonas críticas (taxa de uso, NBR 8800)" % nome_est
        gr.subtitulo = pior_txt or "Taxa de uso das barras"
        gr.legenda = [(c, "taxa " + t) for c, t in CORES_TAXA]
        gr.rodape = "%s · maior taxa %s" % ("Atende" if obj.TaxaMaxima <= 1.0 else "NÃO ATENDE",
                                             _br(obj.TaxaMaxima))
        for k in range(n_cena):
            _balancar(v, k, n_cena)
            gr.quadro()
            if progresso:
                progresso(gr.n)
        gr.quadro(int(fps * 1.5))
    finally:
        try:
            import PrumoAnaliseVista as V
            V.OPCOES["sem_titulo"] = False
        except Exception:
            pass
        obj.Mostrar, obj.Escala, obj.Combinacao = estado
        if transp is not None:
            try:
                est.ViewObject.Transparency = transp
            except Exception:
                pass
        doc.recompute()
    return gr.gravar(caminho)


# ------------------------------------------------------------------ elementos finitos (sólido)
def gravar_fem(estudo, caminho, largura=1280, altura=720, fps=24, segundos=10.0, progresso=None):
    """Vídeo de um estudo FEM estático: a peça deformando (pulsando) com as cores de von Mises.
    No detalhe de ligação (cargas majoradas) o vermelho é fy/γa1: o que fica vermelho atingiu a
    resistência de cálculo. Retorna o arquivo gravado."""
    import PrumoFEM as F
    res = estudo.resultados
    if not res:
        raise ValueError("calcule o estudo antes de gravar o vídeo")
    r = res[0]
    malha = r.Mesh
    if malha is None:
        raise ValueError("o resultado não tem malha")
    e = F.estatisticas(estudo) or {}
    sy = e.get("Sy")
    gama = estudo.get("PrumoGamaA1", 0.0)
    limite = (sy / gama) if (sy and gama) else (sy or max(r.vonMises))
    doc = estudo.doc
    v = FreeCADGui.ActiveDocument.ActiveView
    visiveis = [o for o in doc.Objects if getattr(o, "ViewObject", None) is not None and o.ViewObject.Visibility]
    gr = Gravador(largura, altura, fps)
    vo = malha.ViewObject
    try:
        for o in visiveis:
            o.ViewObject.Visibility = False
        vo.Visibility = True
        modo_antes = vo.DisplayMode
        try:
            vo.DisplayMode = "Faces"
        except Exception:
            pass
        nos = list(r.NodeNumbers)
        # escala fixa de 0 (azul) até o limite (vermelho): o que passa do limite fica vermelho
        # (dois valores de referência no começo fixam a escala; os valores reais vêm depois e valem)
        vo.setNodeColorByScalars([nos[0], nos[0]] + nos, [0.0, limite] + [min(s, limite) for s in r.vonMises])
        vo.setNodeDisplacementByVectors(nos, list(r.DisplacementVectors))
        umax = max((d.Length for d in r.DisplacementVectors), default=0.0)
        bb = malha.FemMesh.BoundBox
        fator_max = (0.04 * bb.DiagonalLength / umax) if umax > 0 else 1.0
        v.viewIsometric()
        v.fitAll()
        detalhe = estudo.get("PrumoDetalhe", False)
        peca = estudo.peca
        nome = peca.Label if peca is not None else "Peça"
        gr.titulo = "%s · tensões e deformação" % nome
        gr.subtitulo = ("%s · cargas majoradas (ELU)" % estudo.get("PrumoCombinacao", "")) if detalhe else \
            "Estática linear · deformação exagerada"
        lim_txt = "fy/γa1 = %s MPa" % _br(limite, 0) if (sy and gama) else "%s MPa" % _br(limite, 0)
        gr.legenda = [((0, 200, 0), "0 MPa"), ((255, 230, 0), "metade de %s" % lim_txt),
                      ((255, 0, 0), "%s ou mais (zona de perigo)" % lim_txt)]
        txt = "σ von Mises máx. %s MPa" % _br(e.get("svm_max"), 1)
        if sy and gama:
            txt += " · σ/(fy/γa1) %s" % _br(e["svm_max"] / limite)
        txt += " · deslocamento máx. %s mm" % _br(e.get("u_max"), 3)
        gr.rodape = txt
        n = max(4, int(segundos * fps))
        for k in range(n):
            f = fator_max * (0.5 - 0.5 * math.cos(2 * math.pi * 3 * k / n))
            vo.applyDisplacement(f)
            _balancar(v, k, n, 30.0)
            gr.quadro()
            if progresso:
                progresso(gr.n)
        vo.applyDisplacement(fator_max)
        gr.quadro(int(fps * 1.5))
    finally:
        try:
            vo.applyDisplacement(0.0)
            vo.resetNodeColor()
            vo.resetNodeDisplacement()
        except Exception:
            pass
        vo.Visibility = False
        try:
            vo.DisplayMode = modo_antes
        except Exception:
            pass
        for o in visiveis:
            try:
                o.ViewObject.Visibility = True
            except Exception:
                pass
    return gr.gravar(caminho)


def _cor_escala(x):
    """Azul → ciano → verde → amarelo → vermelho para x de 0 a 1 (acima de 1: vermelho)."""
    x = min(max(x, 0.0), 1.0)
    pts = [(0.0, (0.0, 0.0, 1.0)), (0.25, (0.0, 1.0, 1.0)), (0.5, (0.0, 1.0, 0.0)), (0.75, (1.0, 1.0, 0.0)),
           (1.0, (1.0, 0.0, 0.0))]
    for (a, ca), (b, cb) in zip(pts[:-1], pts[1:]):
        if x <= b:
            t = (x - a) / (b - a)
            return tuple(ca[k] + (cb[k] - ca[k]) * t for k in range(3))
    return pts[-1][1]


def escolher_e_gravar(fn, alvo, sugestao):
    """Pede o arquivo, grava com a barra de progresso e avisa onde ficou."""
    from PySide import QtCore, QtWidgets
    mw = FreeCADGui.getMainWindow()
    filtro = "Vídeo MP4 (*.mp4);;GIF animado (*.gif)" if ffmpeg() else "GIF animado (*.gif)"
    caminho, _f2 = QtWidgets.QFileDialog.getSaveFileName(mw, "Gravar vídeo", sugestao, filtro)
    if not caminho:
        return None
    dlg = QtWidgets.QProgressDialog("Gravando o vídeo…", None, 0, 0, mw)
    dlg.setWindowTitle("Prumo 3D")
    dlg.setWindowModality(QtCore.Qt.WindowModal)
    dlg.show()

    def prog(n):
        dlg.setLabelText("Gravando o vídeo… quadro %d" % n)
        QtWidgets.QApplication.processEvents()
    try:
        saida = fn(alvo, caminho, progresso=prog)
    except Exception as ex:
        dlg.close()
        QtWidgets.QMessageBox.warning(mw, "Gravar vídeo", "Não foi possível gravar o vídeo: %s" % ex)
        return None
    dlg.close()
    QtWidgets.QMessageBox.information(mw, "Gravar vídeo", "Vídeo gravado em:\n%s" % saida)
    return saida

# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: explosão animada da montagem (ideia da bancada Exploded Assembly; código escrito do zero).

Uma "Explosão" guarda passos: em cada passo, peças que saem numa direção por uma distância. Parafusos,
porcas e arruelas do Prumo giram enquanto saem (uma volta por passo de rosca). A barra de 0 a 100 % mostra a
montagem se abrindo passo a passo; Tocar anima, Montada volta tudo ao lugar exato de antes, e as
trajetórias mostram para onde cada peça vai.

As posições de montagem ficam guardadas no próprio objeto Explosão: abrir, animar e fechar não muda o projeto.
"""
import json
import math

import FreeCAD

V = FreeCAD.Vector


def _pl_para_lista(pl):
    return list(pl.Base) + list(pl.Rotation.Q)


def _lista_para_pl(v):
    return FreeCAD.Placement(V(*v[:3]), FreeCAD.Rotation(*v[3:7]))


def passo_rosca(obj):
    """Passo da rosca (mm) de um fixador do Prumo, ou None."""
    if getattr(getattr(obj, "Proxy", None), "__class__", None).__name__ != "Fixador":
        return None
    try:
        import PrumoFixadores
        return float(PrumoFixadores.passo(obj.Diametro))
    except Exception:
        return 1.5


class Explosao:
    def __init__(self, obj):
        obj.Proxy = self
        obj.addProperty("App::PropertyString", "Passos", "Explosão", "Passos (lista em JSON)")
        obj.addProperty("App::PropertyString", "Montada", "Explosão", "Posições de montagem (JSON)")
        obj.addProperty("App::PropertyPercent", "Abertura", "Explosão", "0 = montada, 100 = toda explodida")
        obj.addProperty("App::PropertyBool", "Trajetorias", "Explosão", "Mostrar as linhas de trajetória")
        for p in ("Passos", "Montada"):
            obj.setEditorMode(p, 2)
        obj.Passos = "[]"
        obj.Montada = "{}"

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        if prop == "Abertura" and getattr(obj, "Passos", None) is not None and not getattr(self, "_aplicando", False):
            try:
                self._aplicando = True
                aplicar(obj, obj.Abertura / 100.0)
            finally:
                self._aplicando = False

    def dumps(self):
        return None

    def loads(self, s):
        return None


class VPExplosao:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import PrumoUtil
        return PrumoUtil.icone("explosao.svg")

    def doubleClicked(self, vobj):
        if FreeCAD.GuiUp:
            abrir_painel(vobj.Object)
        return True

    def dumps(self):
        return None

    def loads(self, s):
        return None


def passos(expl):
    return json.loads(expl.Passos or "[]")


def _gravar_passos(expl, lista):
    expl.Passos = json.dumps(lista)


def criar(doc):
    o = doc.addObject("App::FeaturePython", "Explosao")
    Explosao(o)
    o.Label = "Explosão animada"
    if FreeCAD.GuiUp:
        VPExplosao(o.ViewObject)
    return o


def adicionar_passo(expl, objs, direcao, distancia, girar_fixadores=True):
    """Novo passo: `objs` saem na `direcao` por `distancia` (mm)."""
    if not objs:
        raise ValueError("selecione as peças que saem neste passo")
    d = V(direcao)
    if d.Length < 1e-9:
        raise ValueError("direção nula")
    d.normalize()
    montada = json.loads(expl.Montada or "{}")
    lista = passos(expl)
    # a posição de montagem é a de agora, com tudo no lugar (abertura 0)
    if expl.Abertura:
        aplicar(expl, 0.0)
    for o in objs:
        if o.Name not in montada:
            montada[o.Name] = _pl_para_lista(o.Placement)
    expl.Montada = json.dumps(montada)
    lista.append({"objs": [o.Name for o in objs], "dir": list(d), "dist": float(distancia),
                  "girar": bool(girar_fixadores)})
    _gravar_passos(expl, lista)
    return len(lista)


def remover_passo(expl, indice):
    lista = passos(expl)
    if 0 <= indice < len(lista):
        aplicar(expl, 0.0)
        lista.pop(indice)
        _gravar_passos(expl, lista)


def posicoes(expl, t):
    """{nome: Placement} de cada peça com a explosão em `t` (0 a 1). Os passos acontecem um depois do outro."""
    doc = expl.Document
    lista = passos(expl)
    montada = json.loads(expl.Montada or "{}")
    res = {n: _lista_para_pl(v) for n, v in montada.items()}
    n = len(lista)
    if not n:
        return res
    for k, p in enumerate(lista):
        progresso = max(0.0, min(1.0, t * n - k))
        if progresso <= 0:
            continue
        mov = V(*p["dir"]) * (p["dist"] * progresso)
        for nome in p["objs"]:
            if nome not in res:
                continue
            pl = res[nome]
            obj = doc.getObject(nome)
            rot = FreeCAD.Rotation()
            pr = passo_rosca(obj) if (obj is not None and p.get("girar", True)) else None
            if pr:
                eixo = pl.Rotation.multVec(V(0, 0, 1))
                # gira só enquanto ainda está na rosca (até o comprimento do corpo); depois só desliza
                comp = float(getattr(obj, "Comprimento", 0) or 0) or p["dist"]
                voltas = min(p["dist"] * progresso, comp) / pr
                # sai girando como quem desenrosca (sentido anti-horário olhando de frente para a cabeça)
                sinal = 1.0 if eixo.dot(V(*p["dir"])) >= 0 else -1.0
                rot = FreeCAD.Rotation(eixo, sinal * 360.0 * voltas)
            centro = pl.Base
            res[nome] = FreeCAD.Placement(centro + mov, rot.multiply(pl.Rotation))
    return res


def aplicar(expl, t):
    doc = expl.Document
    for nome, pl in posicoes(expl, t).items():
        o = doc.getObject(nome)
        if o is not None:
            o.Placement = pl
    if getattr(expl, "Trajetorias", False):
        trajetorias(expl, True)
    if FreeCAD.GuiUp:
        try:
            import FreeCADGui
            FreeCADGui.updateGui()
        except Exception:
            pass


def trajetorias(expl, mostrar=True):
    """Linhas do lugar de montagem até o fim da explosão, para cada peça (objeto auxiliar, fora da lista)."""
    import Part
    doc = expl.Document
    nome = expl.Name + "_Trajetorias"
    o = doc.getObject(nome)
    if not mostrar:
        if o is not None:
            doc.removeObject(o.Name)
        return None
    ini, fim = posicoes(expl, 0.0), posicoes(expl, 1.0)
    linhas = []
    for n, p0 in ini.items():
        obj = doc.getObject(n)
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        c_local = obj.Shape.BoundBox.Center
        try:
            c_local = obj.Placement.inverse().multVec(c_local)
        except Exception:
            pass
        a = p0.multVec(c_local)
        b = fim[n].multVec(c_local)
        if (b - a).Length > 1e-6:
            linhas.append(Part.LineSegment(a, b).toShape())
    if o is None:
        o = doc.addObject("Part::Feature", nome)
        o.Label = "Trajetórias da explosão"
        if FreeCAD.GuiUp:
            o.ViewObject.LineColor = (0.97, 0.75, 0.0)
            try:
                o.ViewObject.DrawStyle = "Dashed"
            except Exception:
                pass
    o.Shape = Part.Compound(linhas) if linhas else Part.Shape()
    return o


def explosao_do_documento(doc, criar_se_nao=True):
    for o in doc.Objects:
        if getattr(getattr(o, "Proxy", None), "__class__", None).__name__ == "Explosao":
            return o
    return criar(doc) if criar_se_nao else None


# ------------------------------------------------------------------ painel
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtWidgets

    DIRECOES = [("face", "Normal da face selecionada"), ("x", "+X"), ("-x", "−X"), ("y", "+Y"), ("-y", "−Y"),
                ("z", "+Z (para cima)"), ("-z", "−Z")]
    VET = {"x": V(1, 0, 0), "-x": V(-1, 0, 0), "y": V(0, 1, 0), "-y": V(0, -1, 0), "z": V(0, 0, 1),
           "-z": V(0, 0, -1)}

    def _selecao_pecas_e_normal():
        import PrumoDireto as D
        objs, normal = [], None
        for obj, _sub, forma, pto in D.selecao():
            alvo = _componente(obj)
            if alvo not in objs:
                objs.append(alvo)
            if forma is not None and getattr(forma, "ShapeType", "") == "Face":
                try:
                    _p, n = D._ref(forma, pto)
                    normal = n
                except Exception:
                    pass
        return objs, normal

    def _componente(obj):
        """O que se move: o componente direto da montagem, o corpo do recurso ou o próprio objeto."""
        for o in [obj] + list(getattr(obj, "InListRecursive", [])):
            for pai in getattr(o, "InList", []):
                if pai.TypeId == "Assembly::AssemblyObject":
                    return o
        import PrumoDireto as D
        return D.peca_de(obj)

    class PainelExplosao(QtWidgets.QDialog):
        def __init__(self, expl):
            super().__init__(FreeCADGui.getMainWindow())
            import PrumoUI as UI
            self.setObjectName("PrumoUI")
            self.setStyleSheet(UI.qss())
            self.setWindowTitle("Explosão animada")
            self.resize(460, 520)
            self.expl = expl
            lay = QtWidgets.QVBoxLayout(self)
            self.lista = QtWidgets.QListWidget()
            lay.addWidget(QtWidgets.QLabel("Passos (na ordem em que as peças saem)"))
            lay.addWidget(self.lista, 1)
            form = QtWidgets.QFormLayout()
            self.dire = QtWidgets.QComboBox()
            for k, t in DIRECOES:
                self.dire.addItem(t, k)
            self.dist = QtWidgets.QDoubleSpinBox()
            self.dist.setRange(1, 1e6)
            self.dist.setSuffix(" mm")
            self.dist.setValue(100)
            self.girar = QtWidgets.QCheckBox("Parafusos e porcas giram ao sair")
            self.girar.setChecked(True)
            form.addRow("Direção", self.dire)
            form.addRow("Distância", self.dist)
            form.addRow("", self.girar)
            lay.addLayout(form)
            linha = QtWidgets.QHBoxLayout()
            add = QtWidgets.QPushButton("Novo passo com a seleção")
            add.setObjectName("PrumoPrimario")
            add.clicked.connect(self.novo)
            rem = QtWidgets.QPushButton("Tirar passo")
            rem.clicked.connect(self.tirar)
            linha.addWidget(add)
            linha.addWidget(rem)
            lay.addLayout(linha)
            self.barra = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.barra.setRange(0, 100)
            self.barra.setValue(int(expl.Abertura))
            self.barra.valueChanged.connect(self._abrir)
            lay.addWidget(QtWidgets.QLabel("Abertura"))
            lay.addWidget(self.barra)
            ctl = QtWidgets.QHBoxLayout()
            for txt, fn in (("Montada", lambda: self.barra.setValue(0)), ("Tocar", self.tocar),
                            ("Explodida", lambda: self.barra.setValue(100))):
                b = QtWidgets.QPushButton(txt)
                b.clicked.connect(fn)
                ctl.addWidget(b)
            self.traj = QtWidgets.QCheckBox("Trajetórias")
            self.traj.setChecked(bool(expl.Trajetorias))
            self.traj.toggled.connect(self._traj)
            ctl.addWidget(self.traj)
            lay.addLayout(ctl)
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(30)
            self.timer.timeout.connect(self._quadro)
            self.atualizar_lista()

        def atualizar_lista(self):
            self.lista.clear()
            doc = self.expl.Document
            for i, p in enumerate(passos(self.expl)):
                nomes = [doc.getObject(n).Label for n in p["objs"] if doc.getObject(n) is not None]
                d = V(*p["dir"])
                nome_dir = next((t for k, t in DIRECOES if k in VET and (VET[k] - d).Length < 1e-6),
                                "(%.2f; %.2f; %.2f)" % (d.x, d.y, d.z))
                self.lista.addItem("%d. %s — %s mm para %s" % (
                    i + 1, ", ".join(nomes)[:50], ("%.0f" % p["dist"]), nome_dir))

        def novo(self):
            import PrumoAvisoClique as AV
            objs, normal = _selecao_pecas_e_normal()
            k = self.dire.currentData()
            d = normal if k == "face" else VET[k]
            if d is None:
                AV.mostrar("Explosão: selecione uma face para usar a normal dela, ou escolha um eixo.")
                return
            try:
                adicionar_passo(self.expl, objs, d, self.dist.value(), self.girar.isChecked())
            except ValueError as exc:
                AV.mostrar("Explosão: %s." % exc)
                return
            self.atualizar_lista()
            self.barra.setValue(100)
            self._abrir(100)

        def tirar(self):
            i = self.lista.currentRow()
            if i < 0:
                return
            remover_passo(self.expl, i)
            self.atualizar_lista()
            self._abrir(self.barra.value())

        def _abrir(self, v):
            self.expl.Abertura = int(v)

        def _traj(self, on):
            self.expl.Trajetorias = bool(on)
            trajetorias(self.expl, bool(on))

        def tocar(self):
            if self.timer.isActive():
                self.timer.stop()
                return
            if self.barra.value() >= 100:
                self.barra.setValue(0)
            self.timer.start()

        def _quadro(self):
            n = max(1, len(passos(self.expl)))
            v = self.barra.value() + max(1, int(round(100.0 / (n * 50))))      # ~1,5 s por passo
            if v >= 100:
                v = 100
                self.timer.stop()
            self.barra.setValue(v)

        def closeEvent(self, ev):
            self.timer.stop()
            super().closeEvent(ev)

    _P = {"p": None}

    def abrir_painel(expl=None):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            raise ValueError("nenhum projeto aberto")
        expl = expl or explosao_do_documento(doc)
        p = PainelExplosao(expl)
        _P["p"] = p
        p.show()
        return p

    class CmdExplosao:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("explosao.svg"), "MenuText": "Explosão animada",
                    "ToolTip": "Passos de explosão da montagem com animação: selecione as peças, a direção e a "
                               "distância; parafusos giram ao sair; barra de 0 a 100 % e trajetórias."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            abrir_painel()

    def registrar_comandos():
        FreeCADGui.addCommand("Prumo_Explosao", CmdExplosao())

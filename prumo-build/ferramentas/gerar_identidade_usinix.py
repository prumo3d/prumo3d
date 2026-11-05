"""Usinix: gera a identidade visual a partir do Conceito A (cubo isométrico com o canto chanfrado).

Saídas (mesmos nomes de antes, para nenhuma referência quebrar):
  src/Mod/Prumo3D/Resources/icons/prumo.svg, prumo.png (256), prumo_64.png, prumo.ico   símbolo colorido
  src/Main/icon.ico, package/WindowsInstaller/icons/FreeCAD.ico, prumo-build/icones/*.ico   ícone do app
  src/Gui/Icons/freecad.svg, freecad-icon-{16,32,48,64}.png                               ícone da janela
  prumo-build/ferramentas/splash/splash_base.png                                          tela de abertura (sem selo)

Cores do modelo: faces #4A86C5 (topo), #0F3D6E (esquerda), #1E5A96 (direita), chanfro #F2A900;
ícone do app em fundo #0F2A4A com faces claras. Fonte: Sora (SIL OFL 1.1, em splash/fontes).
"""
import os

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
FONTES = os.path.join(AQUI, "splash", "fontes")

# geometria do modelo (viewBox 0 0 200 200)
TOPO = [(100, 40), (152, 70), (115.6, 91), (84.4, 91), (48, 70)]
ESQ = [(48, 70), (84.4, 91), (100, 118), (100, 160), (48, 130)]
DIR = [(115.6, 91), (152, 70), (152, 130), (100, 160), (100, 118)]
CHANFRO = [(84.4, 91), (115.6, 91), (100, 118)]

CORES = {"topo": "#4A86C5", "esq": "#0F3D6E", "dir": "#1E5A96", "chanfro": "#F2A900"}
CORES_CLARAS = {"topo": "#E8F0FA", "esq": "#8FB4DE", "dir": "#BFD4EE", "chanfro": "#F2A900"}
FUNDO_APP = "#0F2A4A"


def svg_simbolo(cores=CORES, fundo=None):
    def pts(p):
        return " ".join("%g,%g" % xy for xy in p)
    corpo = ""
    if fundo:
        corpo += '<rect x="4" y="4" width="192" height="192" rx="44" fill="%s"/>' % fundo
    for nome, p in (("topo", TOPO), ("esq", ESQ), ("dir", DIR), ("chanfro", CHANFRO)):
        corpo += '<polygon points="%s" fill="%s"/>' % (pts(p), cores[nome])
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">'
            '<title>Usinix</title>%s</svg>\n' % corpo)


def desenhar(lado, cores=CORES, fundo=None, margem=0.0):
    """Símbolo rasterizado (supersample 4x). margem: fração do lado deixada em volta do cubo."""
    s = 4
    n = lado * s
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fundo:
        d.rounded_rectangle([0.02 * n, 0.02 * n, 0.98 * n, 0.98 * n], radius=int(0.22 * n), fill=fundo)
    # o cubo ocupa x 48–152, y 40–160 no viewBox; centraliza e escala
    escala = (1 - 2 * margem) * n / 200.0
    off = margem * n

    def t(p):
        return [(off + x * escala, off + y * escala) for x, y in p]
    for nome, p in (("topo", TOPO), ("esq", ESQ), ("dir", DIR), ("chanfro", CHANFRO)):
        d.polygon(t(p), fill=cores[nome])
    return im.resize((lado, lado), Image.LANCZOS)


def icone_app(lado):
    # nos tamanhos pequenos o fundo escuro some: cubo colorido, maior, sem fundo
    if lado <= 24:
        return desenhar(lado, CORES, None, margem=-0.12)
    return desenhar(lado, CORES_CLARAS, FUNDO_APP, margem=0.0)


def salvar_ico(caminho, tamanhos=(16, 24, 32, 48, 64, 128, 256)):
    imgs = [icone_app(t) for t in tamanhos]
    imgs[-1].save(caminho, format="ICO", sizes=[(t, t) for t in tamanhos], append_images=imgs[:-1])


def fonte(peso, tam):
    return ImageFont.truetype(os.path.join(FONTES, "Sora-%s.ttf" % peso), tam)


def splash(caminho):
    W, H = 960, 540
    faixa = 450                       # onde começa a faixa branca de baixo
    im = Image.new("RGB", (W, H), FUNDO_APP)
    d = ImageDraw.Draw(im)
    # degradê vertical discreto do azul-noite para o azul do lado esquerdo do cubo
    a, b = (0x0F, 0x2A, 0x4A), (0x0F, 0x3D, 0x6E)
    for y in range(faixa):
        k = y / float(faixa)
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    # malha isométrica bem fraca (desenho técnico)
    grade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grade)
    passo = 40
    for x0 in range(-H * 2, W + H * 2, passo):
        g.line([(x0, 0), (x0 + faixa * 1.732, faixa)], fill=(255, 255, 255, 14))
        g.line([(x0, 0), (x0 - faixa * 1.732, faixa)], fill=(255, 255, 255, 14))
    im.paste(grade, (0, 0), grade)
    # cubo em linha fina à direita (eco do símbolo)
    eco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    e = ImageDraw.Draw(eco)
    esc, ox, oy = 1.9, 640, 10

    def tt(p):
        return [(ox + x * esc, oy + y * esc) for x, y in p]
    for p in (TOPO, ESQ, DIR, CHANFRO):
        q = tt(p)
        e.line(q + [q[0]], fill=(255, 255, 255, 40), width=1)
    im.paste(eco, (0, 0), eco)
    # ícone do app
    ic = icone_app(190)
    im.paste(ic, (92, 128), ic)
    ImageDraw.Draw(im).rounded_rectangle([93, 129, 92 + 188, 128 + 188], radius=41, outline="#3A6EA8", width=2)
    # nome e linhas
    d = ImageDraw.Draw(im)
    d.text((330, 150), "usinix", font=fonte("700", 92), fill="#FFFFFF")
    d.rectangle([336, 262, 456, 268], fill=CORES["chanfro"])
    d.text((334, 286), "O CAD 3D da metal-mecânica, em português", font=fonte("400", 20), fill="#D6E2F0")
    d.text((334, 320), "Baseado no FreeCAD 1.1 · software livre (LGPL)", font=fonte("400", 14), fill="#8FA9C6")
    # faixa branca de baixo
    d.rectangle([0, faixa, W, H], fill="#FFFFFF")
    d.rectangle([0, faixa - 4, W, faixa], fill=CORES["chanfro"])
    d.text((W - 40, faixa + 30), "USINIX", font=fonte("700", 15), fill=FUNDO_APP, anchor="rm")
    d.text((W - 40, faixa + 56), "software livre e gratuito", font=fonte("400", 12), fill="#5A6778", anchor="rm")
    im.save(caminho, optimize=True)


def main():
    icons = os.path.join(RAIZ, "src", "Mod", "Prumo3D", "Resources", "icons")
    open(os.path.join(icons, "prumo.svg"), "w", encoding="utf-8").write(svg_simbolo())
    desenhar(256).save(os.path.join(icons, "prumo.png"), optimize=True)
    desenhar(64).save(os.path.join(icons, "prumo_64.png"), optimize=True)
    salvar_ico(os.path.join(icons, "prumo.ico"))
    for destino in (os.path.join(RAIZ, "src", "Main", "icon.ico"),
                    os.path.join(RAIZ, "package", "WindowsInstaller", "icons", "FreeCAD.ico"),
                    os.path.join(RAIZ, "prumo-build", "icones", "FreeCAD.ico"),
                    os.path.join(RAIZ, "prumo-build", "icones", "icon.ico")):
        salvar_ico(destino)
    gui = os.path.join(RAIZ, "src", "Gui", "Icons")
    open(os.path.join(gui, "freecad.svg"), "w", encoding="utf-8").write(svg_simbolo(CORES_CLARAS, FUNDO_APP))
    open(os.path.join(RAIZ, "prumo-build", "icones", "freecad.svg"), "w", encoding="utf-8").write(
        svg_simbolo(CORES_CLARAS, FUNDO_APP))
    for t in (16, 32, 48, 64):
        for pasta in (gui, os.path.join(RAIZ, "prumo-build", "icones")):
            icone_app(t).save(os.path.join(pasta, "freecad-icon-%d.png" % t), optimize=True)
    splash(os.path.join(AQUI, "splash", "splash_base.png"))
    print("identidade Usinix gerada")


if __name__ == "__main__":
    main()

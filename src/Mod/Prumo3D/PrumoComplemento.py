# SPDX-License-Identifier: LGPL-2.1-or-later
"""Atualização só do complemento Prumo 3D (sem baixar o pacote inteiro).

O pacote completo (instalador, .7z, AppImage) traz o FreeCAD de base e o complemento Prumo3D em
<programa>/Mod/Prumo3D. Quando uma versão nova muda só o complemento, a página de versões publica também
Prumo3D_<versão>-complemento.zip (poucos MB). A atualização grava esse complemento em

    <dados do usuário>/Mod/Prumo3D

e o próprio FreeCAD dá preferência ao módulo da pasta do usuário sobre o de mesmo nome da pasta do
programa (FreeCADInit.InitApplications). Nada pede permissão de administrador.

O caminho de volta também é automático: o Init.py / InitGui.py da cópia da pasta do usuário passam a vez ao
complemento da pasta do programa quando

- um pacote completo mais novo foi instalado depois (a cópia do usuário ficou para trás);
- a base de FreeCAD mudou e a cópia não foi feita para ela (complemento.json);
- as duas últimas aberturas com a cópia do usuário não terminaram bem.
"""

import json
import os
import re
import sys

import FreeCAD

MANIFESTO = "complemento.json"
CONTADOR = "aberturas.json"
TENTATIVAS_MAX = 2

# a partir de qual pacote completo um complemento pode ser aplicado (muda quando a base de FreeCAD ou as
# bibliotecas do pacote mudam: aí só o pacote completo serve)
BASE_MINIMA = "1.1.0"

_estado = {"aqui": None, "usuario": False, "delegou": None, "motivo": ""}


# ----------------------------------------------------------------------------------- versões e pastas
def _chave(rotulo):
    r = (rotulo or "").strip().lstrip("vV")
    v, _, canal = r.partition("-")
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
    return _chave(a) > _chave(b)


def ler_versao(pasta):
    """Rótulo da versão do complemento de uma pasta, lendo os arquivos (sem importar)."""
    for nome, padrao in (("PrumoVersaoCompilada.py", r'VERSAO_COMPILADA\s*=\s*"([^"]*)"'),
                         ("PrumoVersao.py", r'^VERSAO\s*=\s*"([^"]*)"')):
        try:
            with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                m = re.search(padrao, f.read(), re.M)
            if m and m.group(1):
                return m.group(1)
        except OSError:
            continue
    return ""


def _norm(p):
    return os.path.normcase(os.path.realpath(p)) if p else ""


def pasta_usuario():
    return os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "Prumo3D")


def pasta_trabalho():
    """Pasta de preparo, FORA de Mod (tudo o que está em Mod o FreeCAD carrega como módulo)."""
    return os.path.join(FreeCAD.getUserAppDataDir(), "Prumo3D-complemento")


def pasta_programa():
    return os.path.join(FreeCAD.getHomePath(), "Mod", "Prumo3D")


def base_freecad():
    v = FreeCAD.Version()
    txt = "%s.%s" % (v[0], v[1])
    if len(v) > 2 and v[2]:
        txt += "." + str(v[2])
    return txt


def _json(caminho, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _gravar_json(caminho, dados):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)


def compativel(manifesto, versao_programa, freecad=None):
    """(True, "") se o complemento serve sobre o pacote completo `versao_programa`; senão (False, motivo)."""
    if not manifesto:
        return False, "sem complemento.json"
    fc = manifesto.get("freecad")
    base = freecad or base_freecad()
    if fc and fc != base:
        return False, "feito para a base FreeCAD %s (esta é %s)" % (fc, base)
    bm = manifesto.get("base_minima") or BASE_MINIMA
    if versao_programa and mais_nova(bm, versao_programa):
        return False, "pede o pacote completo %s ou mais novo (o instalado é %s)" % (bm, versao_programa)
    return True, ""


def versao_programa():
    """Versão do pacote completo instalado (o complemento da pasta do programa)."""
    return ler_versao(pasta_programa())


# ----------------------------------------------------------------------------------- ao abrir
def motivo_para_voltar(aqui):
    """Se o complemento em `aqui` (cópia da pasta do usuário) deve passar a vez ao da pasta do programa, o
    motivo; senão ''."""
    prog = pasta_programa()
    if not os.path.isfile(os.path.join(prog, "InitGui.py")):
        return ""
    meu, dele = ler_versao(aqui), ler_versao(prog)
    if dele and not mais_nova(meu, dele):
        return "o pacote instalado (%s) é igual ou mais novo que o complemento da pasta do usuário (%s)" % (dele, meu)
    man = _json(os.path.join(aqui, MANIFESTO))
    if man is not None:
        ok, motivo = compativel(man, dele)
        if not ok:
            return motivo
    if int((_json(os.path.join(aqui, CONTADOR), {}) or {}).get("tentativas", 0)) >= TENTATIVAS_MAX:
        return "o complemento %s não abriu nas últimas tentativas" % meu
    return ""


def ativar(origem):
    """Chamado pelo Init.py e pelo InitGui.py. Devolve a pasta do complemento do programa para onde passar a
    vez, ou None (segue com o próprio).

    Só a cópia da pasta do usuário pode passar a vez; a do programa sempre roda a si mesma."""
    aqui = os.path.dirname(os.path.abspath(origem or __file__))
    if _estado["aqui"] is None:
        _estado["aqui"] = aqui
        _estado["usuario"] = _norm(aqui) == _norm(pasta_usuario()) and _norm(aqui) != _norm(pasta_programa())
        if _estado["usuario"]:
            motivo = motivo_para_voltar(aqui)
            if motivo:
                _estado["delegou"] = pasta_programa()
                _estado["motivo"] = motivo
                _usar(pasta_programa(), aqui)
                FreeCAD.Console.PrintLog("Prumo: usando o complemento do programa (%s)\n" % motivo)
            else:
                _contar(aqui)
    if _norm(aqui) == _norm(_estado["delegou"]):
        return None
    return _estado["delegou"]


def _contar(aqui):
    p = os.path.join(aqui, CONTADOR)
    c = _json(p, {}) or {}
    c["tentativas"] = int(c.get("tentativas", 0)) + 1
    try:
        _gravar_json(p, c)
    except OSError:
        pass


def abriu_bem():
    """A interface abriu com a cópia da pasta do usuário: zera as tentativas."""
    if not _estado["usuario"] or _estado["delegou"]:
        return
    p = os.path.join(_estado["aqui"], CONTADOR)
    try:
        _gravar_json(p, {"tentativas": 0})
    except OSError:
        pass


def _limpar_modulos():
    for nome in list(sys.modules):
        if nome.startswith("Prumo") and nome != __name__:
            sys.modules.pop(nome, None)


def _usar(dest, sair):
    for p in list(sys.path):
        if _norm(p) == _norm(sair):
            sys.path.remove(p)
    if dest not in sys.path:
        sys.path.insert(0, dest)
    _limpar_modulos()


def falhou(exc):
    """A cópia da pasta do usuário deu erro ao carregar: passa a vez ao programa nesta sessão e nas próximas."""
    aqui = _estado["aqui"]
    if aqui:
        try:
            _gravar_json(os.path.join(aqui, CONTADOR), {"tentativas": TENTATIVAS_MAX, "erro": str(exc)[:500]})
        except OSError:
            pass
    _estado["delegou"] = pasta_programa()
    _estado["motivo"] = "erro ao carregar: %s" % exc
    _usar(pasta_programa(), aqui or "")
    FreeCAD.Console.PrintError("Prumo: o complemento atualizado falhou (%s); usando o instalado.\n" % exc)
    return pasta_programa()


def executar(arquivo, ambiente):
    """Roda o Init.py / InitGui.py de outra pasta no mesmo ambiente que o FreeCAD deu a este."""
    with open(arquivo, encoding="utf-8") as f:
        codigo = compile(f.read(), arquivo, "exec")
    ambiente["__file__"] = arquivo
    exec(codigo, ambiente)


def estado():
    return dict(_estado)


# ----------------------------------------------------------------------------------- instalar um .zip
def instalar_zip(arquivo, versao_programa_=None):
    """Confere o complemento baixado (.zip) e instala em <dados do usuário>/Mod/Prumo3D. Vale ao abrir o
    Prumo de novo. Devolve a versão. Lança ValueError com o motivo se o arquivo não serve."""
    import shutil
    import zipfile
    dest = pasta_usuario()
    mod = os.path.dirname(dest)
    os.makedirs(mod, exist_ok=True)
    trab = pasta_trabalho()
    os.makedirs(trab, exist_ok=True)
    with zipfile.ZipFile(arquivo) as z:
        nomes = z.namelist()
        for n in nomes:
            partes = n.replace("\\", "/").split("/")
            if n.startswith("/") or ".." in partes or (partes and partes[0] != "Prumo3D"):
                raise ValueError("arquivo com caminho inválido: %s" % n)
        for obrig in ("Init.py", "InitGui.py", "PrumoVersao.py", MANIFESTO):
            if "Prumo3D/" + obrig not in nomes:
                raise ValueError("o arquivo não é um complemento do Prumo 3D (falta %s)" % obrig)
        manifesto = json.loads(z.read("Prumo3D/" + MANIFESTO).decode("utf-8"))
        versao = manifesto.get("versao", "")
        prog = versao_programa_ if versao_programa_ is not None else versao_programa()
        if prog and not mais_nova(versao, prog):
            raise ValueError("o pacote instalado (%s) já é igual ou mais novo que este complemento (%s)" % (prog, versao))
        ok, motivo = compativel(manifesto, prog)
        if not ok:
            raise ValueError("este complemento não serve nesta instalação: " + motivo)
        tmp = os.path.join(trab, "Prumo3D.parte")
        if os.path.isdir(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        for info in z.infolist():
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if not rel or info.is_dir():
                continue
            alvo = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(alvo), exist_ok=True)
            with z.open(info) as src, open(alvo, "wb") as out:
                shutil.copyfileobj(src, out)
    if ler_versao(tmp) != versao:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError("a versão dentro do complemento não confere com o complemento.json")
    # troca: a cópia antiga (se houver) sai para Prumo3D.antigo e é apagada; a nova entra no lugar
    antigo = os.path.join(trab, "Prumo3D.antigo")
    if os.path.isdir(antigo):
        shutil.rmtree(antigo, ignore_errors=True)
    if os.path.isdir(dest):
        os.replace(dest, antigo)
    os.replace(tmp, dest)
    shutil.rmtree(antigo, ignore_errors=True)
    return versao


def remover_copia_do_usuario():
    """Volta ao complemento do pacote instalado (apaga a cópia da pasta do usuário). Vale ao abrir de novo."""
    import shutil
    d = pasta_usuario()
    if os.path.isdir(d) and _norm(d) != _norm(pasta_programa()):
        os.makedirs(pasta_trabalho(), exist_ok=True)
        antigo = os.path.join(pasta_trabalho(), "Prumo3D.antigo")
        if os.path.isdir(antigo):
            shutil.rmtree(antigo, ignore_errors=True)
        os.replace(d, antigo)
        shutil.rmtree(antigo, ignore_errors=True)
        return True
    return False

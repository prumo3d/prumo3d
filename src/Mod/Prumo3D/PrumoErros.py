# SPDX-License-Identifier: LGPL-2.1-or-later
"""Mensagens de erro do FreeCAD em português.

As operações (extrusão, casca, arredondar…) devolvem o erro como texto em inglês, e o FreeCAD mostra esse
texto direto na caixa de aviso, sem passar pela tradução. Aqui fica a tradução desses textos e um filtro
que troca o texto das caixas de aviso na hora em que aparecem.
"""

import re

ERROS = {
    # Arredondar, chanfro, casca, ângulo de saída
    "A fatal error occurred when making fillets": "Não foi possível arredondar: erro grave no núcleo geométrico.",
    "Failed to make thick solid": "Não foi possível fazer a casca. Tente uma espessura menor, outro modo de "
                                  "junção ou escolha outras faces para abrir.",
    "Resulting shape is invalid": "A forma resultante ficou inválida.",
    "Resulting shape is null": "A operação não gerou forma nenhuma.",
    "Resulting shape is not a solid": "A forma resultante não é um sólido.",
    "Error: Result is not a solid": "O resultado não é um sólido.",
    "Error: Result is self intersecting": "O resultado cruza a si mesmo.",
    "No edges specified": "Nenhuma aresta escolhida.",
    "Invalid edge link": "Aresta escolhida inválida.",
    "Edge link size mismatch": "A quantidade de arestas escolhidas não confere.",
    "Neutral plane reference edge must be linear": "A aresta de referência do plano neutro precisa ser reta.",
    "Neutral plane reference face must be planar": "A face de referência do plano neutro precisa ser plana.",
    "Neutral plane reference must be a face": "A referência do plano neutro precisa ser uma face.",
    "Neutral plane reference must be face of a feature or a datum plane":
        "O plano neutro precisa ser uma face de operação ou um plano de referência.",
    "No neutral plane reference specified": "Escolha o plano neutro.",
    "No neutral plane specified and none can be guessed": "Escolha o plano neutro: não deu para deduzir um.",
    "Failed to extract neutral plane reference edge": "Não deu para usar a aresta do plano neutro.",
    "Failed to extract neutral plane reference face": "Não deu para usar a face do plano neutro.",
    "No pull direction reference specified": "Escolha a direção de saída do molde.",
    "Pull direction reference edge must be linear": "A aresta da direção de saída precisa ser reta.",
    "Pull direction reference must be an edge or a datum line":
        "A direção de saída precisa ser uma aresta ou uma linha de referência.",
    "Failed to extract pull direction reference edge": "Não deu para usar a aresta da direção de saída.",
    # Base e esboço
    "Base feature's TopoShape is invalid": "A forma da operação anterior está inválida.",
    "Base feature's shape is invalid": "A forma da operação anterior está inválida.",
    "Base feature's shape is not a solid": "A operação anterior não é um sólido.",
    "Base feature's shape is not defined": "A operação anterior não tem forma.",
    "Cannot make face from profile": "Não deu para fazer face com o perfil: confira se o esboço está fechado.",
    "Creating face failed (null shape result)": "Não deu para criar a face (o resultado ficou vazio).",
    "Expect exactly one support face": "Escolha exatamente uma face de apoio.",
    "Missing container body": "A operação precisa estar dentro de um corpo.",
    "No profile linked": "Escolha o perfil (esboço ou face).",
    "No valid profile linked": "Escolha um perfil válido (esboço ou face).",
    "No support face specified": "Escolha a face de apoio.",
    "No planar support": "O apoio precisa ser plano.",
    "No support linked": "Escolha o apoio.",
    "Sketch support shape is empty!": "O apoio do esboço está vazio.",
    "Solving the sketch failed": "Não deu para resolver o esboço: confira as restrições.",
    "SketchBased: Failed to extract face": "Não deu para usar a face escolhida.",
    "SketchBased: Must be face of a feature": "Escolha uma face de operação.",
    "SketchBased: No face selected": "Nenhuma face escolhida.",
    "SketchBased: No faces found in this direction": "Nenhuma face encontrada nessa direção.",
    "SketchBased: Up to face: Failed to extract face": "\"Até a face\": não deu para usar a face escolhida.",
    "SketchBased: Up to face: Must not intersect sketch!": "\"Até a face\": a face não pode cortar o esboço.",
    "SketchBased: Up to face: No face found": "\"Até a face\": nenhuma face encontrada.",
    "Missing external geometry reference": "Falta a referência de uma geometria externa do esboço.",
    # Extrusão, revolução, ranhura
    "FeatureExtrusion: Length: Could not extrude the sketch!": "Não deu para extrudar o esboço com esse comprimento.",
    "Total length of extrusion is zero.": "O comprimento total da extrusão é zero.",
    "Extrude: Can only offset one face": "A extrusão só desloca uma face.",
    "Direction is zero-length": "A direção tem comprimento zero.",
    "Direction edge must be a straight line": "A aresta de direção precisa ser reta.",
    "Direction face must be planar": "A face de direção precisa ser plana.",
    "Direction reference must be edge or face": "A direção precisa ser uma aresta ou uma face.",
    "Failed to extract direction edge": "Não deu para usar a aresta de direção.",
    "Failed to extract direction plane": "Não deu para usar o plano de direção.",
    "No direction reference specified": "Escolha a direção.",
    "Cannot create a revolution with zero angle.": "A revolução precisa de ângulo maior que zero.",
    "Could not revolve the sketch!": "Não deu para girar o esboço.",
    "Axis must not be parallel to the sketch plane": "O eixo não pode ser paralelo ao plano do esboço.",
    "Axis must not be perpendicular to the sketch plane": "O eixo não pode ser perpendicular ao plano do esboço.",
    "Axis reference must be an edge": "O eixo precisa ser uma aresta.",
    "Axis reference must be edge of a feature or datum line":
        "O eixo precisa ser uma aresta de operação ou uma linha de referência.",
    "No axis reference specified": "Escolha o eixo.",
    "No rotation axis reference specified": "Escolha o eixo de rotação.",
    "No valid axis specified": "Escolha um eixo válido.",
    "Failed to extract axis edge": "Não deu para usar a aresta do eixo.",
    "Failed to extract rotation edge": "Não deu para usar a aresta de rotação.",
    "Rotation edge must be a straight line, circle or arc of circle":
        "A aresta de rotação precisa ser reta, círculo ou arco.",
    "Edge must be a straight line, circle or arc of circle": "A aresta precisa ser reta, círculo ou arco.",
    "Groove up to first is not yet supported": "Ranhura \"até a primeira face\" ainda não é possível.",
    "Revolve up to first is not yet supported": "Revolução \"até a primeira face\" ainda não é possível.",
    # Padrões e espelho
    "At least one occurrence required": "É preciso pelo menos uma ocorrência.",
    "At least two occurrences required": "É preciso pelo menos duas ocorrências.",
    "Pattern angle can't be null": "O ângulo do padrão não pode ser zero.",
    "Pattern length too small": "O comprimento do padrão é pequeno demais.",
    "Scaling factor too small": "O fator de escala é pequeno demais.",
    "Mirror face must be planar": "A face de espelho precisa ser plana.",
    "No mirror plane reference specified": "Escolha o plano de espelho.",
    "Failed to extract mirror plane": "Não deu para usar o plano de espelho.",
    # Varredura, loft, hélice
    "A fatal error occurred when making the sweep": "Não foi possível fazer a varredura: erro grave no núcleo "
                                                    "geométrico.",
    "Invalid spine": "Caminho da varredura inválido.",
    "Invalid spine.": "Caminho da varredura inválido.",
    "No spine": "Escolha o caminho da varredura.",
    "No spine linked": "Escolha o caminho da varredura.",
    "No sections linked.": "Escolha as seções.",
    "Invalid section link": "Seção escolhida inválida.",
    "Pipe: Invalid profile/section": "Varredura: perfil ou seção inválido.",
    "Section failed": "Não deu para usar a seção.",
    "No valid data given for linear scaling": "Faltam dados para a escala linear.",
    "No valid data given for S-shape scaling": "Faltam dados para a escala em S.",
    "Error: Thread could not be built": "Não foi possível fazer a rosca.",
    "Thread fit out of range": "Folga da rosca fora da faixa.",
    "Thread size out of range": "Tamanho da rosca fora da faixa.",
    "Thread type is invalid": "Tipo de rosca inválido.",
    "Thread type out of range": "Tipo de rosca fora da faixa.",
    # Primitivas e Part
    "Height of box too small": "A altura da caixa é pequena demais.",
    "Length of box too small": "O comprimento da caixa é pequeno demais.",
    "Width of box too small": "A largura da caixa é pequena demais.",
    "Input shape is null": "A forma de entrada está vazia.",
    "Null shape": "Forma vazia.",
    "Shape is null.": "Forma vazia.",
    "No shape linked.": "Escolha a forma.",
    "No shapes linked": "Escolha as formas.",
    "No input shapes!": "Escolha as formas.",
    "No object linked": "Escolha o objeto.",
    "No part object linked.": "Escolha a peça.",
    "No source shape linked.": "Escolha a forma de origem.",
    "Not enough shape objects linked": "Escolha mais formas.",
    "Linked object is not a Part object": "O objeto escolhido não é uma peça.",
    "Linked shape object is empty": "A forma escolhida está vazia.",
    "Linked shape object is not a wire": "A forma escolhida não é uma linha contínua.",
    "Invalid source link": "Origem escolhida inválida.",
    "Invalid source shape": "Forma de origem inválida.",
    "Source shape is not single solid.": "A forma de origem precisa ser um sólido só.",
    "No solid": "Não há sólido.",
    "MultiFusion failed": "Não deu para unir as formas.",
    "Mode 'Recto-Verso' is not supported for 2D offset.": "O modo \"frente e verso\" não vale para "
                                                          "deslocamento 2D.",
    "Body: object is not allowed": "Esse objeto não pode entrar no corpo.",
    "Invalid face selection": "Face escolhida inválida.",
    "Unable to calculate intersection points": "Não deu para calcular os pontos de interseção.",
    "User aborted": "Cancelado.",
    # Genérico do painel de operação
    "The feature could not be created with the given parameters.\nThe geometry may be invalid or the parameters "
    "may be incompatible.\nPlease adjust the parameters and try again.":
        "Não foi possível criar a operação com esses valores.\nA geometria pode estar inválida ou os valores "
        "incompatíveis.\nAjuste os valores e tente de novo.",
}

# títulos das caixas de aviso
TITULOS = {"Input error": "Erro de entrada", "Error": "Erro", "Warning": "Aviso", "Wrong selection": "Seleção errada",
           "Selection error": "Erro de seleção"}


def traduzir(texto):
    """Texto em português, ou None se não houver tradução."""
    if not texto:
        return None
    t = texto.strip()
    if t in ERROS:
        return ERROS[t]
    # "Prefixo: mensagem" (ex.: "Pad: Resulting shape is not a solid")
    m = re.match(r"^([\w :]+?):\s+(.+)$", t, re.S)
    if m and m.group(2).strip() in ERROS:
        return ERROS[m.group(2).strip()]
    return None


try:
    from PySide import QtCore, QtWidgets

    class FiltroAvisos(QtCore.QObject):
        """Troca o texto das caixas de aviso do FreeCAD (erros das operações) pelo português."""

        def eventFilter(self, obj, ev):
            try:
                if ev.type() == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QMessageBox):
                    pt = traduzir(obj.text())
                    if pt:
                        obj.setText(pt)
                    tt = TITULOS.get(obj.windowTitle())
                    if tt:
                        obj.setWindowTitle(tt)
            except Exception:
                pass
            return False
except ImportError:  # pragma: no cover
    FiltroAvisos = None

_estado = {"filtro": None}


def instalar():
    if FiltroAvisos is None or _estado["filtro"] is not None:
        return _estado["filtro"]
    app = QtWidgets.QApplication.instance()
    if app is None:
        return None
    f = FiltroAvisos(app)
    app.installEventFilter(f)
    _estado["filtro"] = f
    return f

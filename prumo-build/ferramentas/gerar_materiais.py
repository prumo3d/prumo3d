"""Gera os cartões de material (.FCMat) da biblioteca Prumo — só materiais usados no Brasil.

A biblioteca do sistema do FreeCAD (materiais europeus, plásticos, madeiras, concreto) fica
desligada no Prumo; ficam esta biblioteca, as aparências e os fluidos (ver PrumoGui).

Valores de resistência = mínimos da especificação (limite de escoamento mínimo e limite inferior
da resistência à tração). Onde a norma não garante propriedade mecânica (SAE em barra/chapa,
ligas para construção mecânica, ferro fundido, alumínio e latão sem mínimo consultado), o cartão
não traz resistência: use o certificado do material. Conferência em 17/10/2026 e 20/10/2026:
- ASTM A36, A572 Gr 50, NBR 7007 MR250/AR350/AR350 COR: ArcelorMittal, Perfis e Barras (2017/2019)
- NBR 6648 CG250, NBR 6650 CFQ250: ArcelorMittal, Chapas/Tiras/Blanks/Rolos (2019)
- A283 Gr C: aasteel.com/a-283, Usiminas Chapas Grossas · A285 Gr C: aasteel.com/sa-285, SSAB
- A516 Gr 60/70: epcland.com, Usiminas Chapas Grossas · A515 Gr 70: aasteel.com/sa-515
- A106 Gr B: projectmaterials.com · A53 Gr B: fedsteel.com · A105: projectmaterials.com
- A500 Gr B (redondo): ASTM A500 (Wikipedia)
- Inox 304/304L: ASTM A213/A240 (tubingchina); 316: Rolled Alloys; 316L: Aperam, "Aço Inox
  Especificações Técnicas" (mínimos ASTM); E do 316L e do 430: Aperam
- 6061-T6 (B209): matmatch.com · 1100-H14, 5052: MakeItFrom (ρ, E, ν)
- SAE 4140/4340/8620, FE 50007, latão C36000: MakeItFrom (ρ, E, ν; resistência depende do estado)
- Ferro fundido cinzento: só densidade típica (E varia muito com a classe: a conferir)
Módulo de elasticidade do aço carbono: ASME B31.1 a 21 °C (29,5e6 psi ≈ 203 GPa) via Engineering
ToolBox. Densidade e Poisson do aço carbono e do inox austenítico: valores típicos.
"""
import os
import re
import shutil
import sys
import uuid

NS = uuid.UUID("5e40c0a0-5e40-4c0a-8e40-5e40c0a05e40")
M_FATHER = "9cdda8b6-b606-4778-8f13-3934d8668e67"
M_STD = "1e2c0088-904a-4537-925f-64064c07d700"
M_LIN = "7b561d1d-fb9b-44f6-9da9-56a4f74d7536"
M_DENS = "454661e5-265b-4320-8e6f-fcf6223ac3af"

AC = dict(E=203000, nu=0.3, rho=7850)        # aço carbono / baixa liga
INOX = dict(E=195000, nu=0.3, rho=8000)      # austenítico
INOX316L = dict(E=193000, nu=0.3, rho=8000)  # Aperam
INOX430 = dict(E=200000, nu=0.3, rho=7800)   # ferrítico, Aperam
AL = dict(E=69000, nu=0.33, rho=2700)
AL1100 = dict(E=69000, nu=0.33, rho=2700)    # MakeItFrom 1100-H14
AL5052 = dict(E=68000, nu=0.33, rho=2700)    # MakeItFrom 5052
LIGADO = dict(E=190000, nu=0.29, rho=7800)   # MakeItFrom 4140/4340/8620
NODULAR = dict(E=180000, nu=0.29, rho=7100)  # MakeItFrom ISO 500-7
LATAO = dict(E=100000, nu=0.31, rho=8200)    # MakeItFrom C36000
CINZENTO = dict(E=None, nu=None, rho=7200)   # E varia com a classe: a conferir

# (pasta, nome, norma, grau, tipo, Sy, Su, base, fonte)
MATERIAIS = [
    # aços estruturais (perfis, chapas, tubos)
    ("Acos estruturais", "ASTM A36", "ASTM A36", "", "Aço carbono estrutural", 250, 400, AC, "ArcelorMittal"),
    ("Acos estruturais", "NBR 7007 MR250", "ABNT NBR 7007", "MR250", "Aço carbono estrutural", 250, 400, AC,
     "ArcelorMittal"),
    ("Acos estruturais", "NBR 7007 AR350", "ABNT NBR 7007", "AR350", "Aço de alta resistência e baixa liga", 350,
     450, AC, "ArcelorMittal"),
    ("Acos estruturais", "NBR 7007 AR350 COR", "ABNT NBR 7007", "AR350 COR",
     "Aço patinável (resistente à corrosão atmosférica)", 350, 485, AC, "ArcelorMittal Perfis e Barras 2019"),
    ("Acos estruturais", "ASTM A572 Gr 50", "ASTM A572", "Grade 50", "Aço de alta resistência e baixa liga", 345,
     450, AC, "ArcelorMittal"),
    ("Acos estruturais", "ASTM A283 Gr C", "ASTM A283", "Grade C", "Aço carbono para chapas", 205, 380, AC,
     "aasteel.com, Usiminas"),
    ("Acos estruturais", "NBR 6648 CG250", "ABNT NBR 6648", "CG250", "Chapa grossa estrutural", 250, 400, AC,
     "ArcelorMittal Chapas 2019"),
    ("Acos estruturais", "NBR 6650 CFQ250", "ABNT NBR 6650", "CFQ250", "Chapa fina a quente estrutural", 250, 400,
     AC, "ArcelorMittal Chapas 2019"),
    ("Acos estruturais", "ASTM A500 Gr B (tubo redondo)", "ASTM A500", "Grade B",
     "Tubo estrutural conformado a frio", 290, 400, AC, "ASTM A500 (Wikipedia)"),
    # chapas finas de uso geral: a norma SAE só garante a composição química
    ("Chapas de uso geral", "Chapa SAE 1008-1010 (fina a frio)", "SAE J403", "1008/1010",
     "Chapa fina laminada a frio", None, None, AC, ""),
    ("Chapas de uso geral", "Chapa SAE 1020 (fina a quente)", "SAE J403", "1020", "Chapa fina laminada a quente",
     None, None, AC, ""),
    # vasos de pressão
    ("Acos para vasos de pressao", "ASTM A285 Gr C (SA-285 C)", "ASTM A285 / ASME SA-285", "Grade C",
     "Chapa para vaso de pressão", 205, 380, AC, "aasteel.com, SSAB"),
    ("Acos para vasos de pressao", "ASTM A516 Gr 60 (SA-516 60)", "ASTM A516 / ASME SA-516", "Grade 60",
     "Chapa para vaso de pressão", 220, 415, AC, "epcland.com, Usiminas"),
    ("Acos para vasos de pressao", "ASTM A516 Gr 70 (SA-516 70)", "ASTM A516 / ASME SA-516", "Grade 70",
     "Chapa para vaso de pressão", 260, 485, AC, "epcland.com, Usiminas"),
    ("Acos para vasos de pressao", "ASTM A515 Gr 70 (SA-515 70)", "ASTM A515 / ASME SA-515", "Grade 70",
     "Chapa para vaso de pressão", 260, 485, AC, "aasteel.com"),
    # tubos e forjados
    ("Tubos e forjados", "ASTM A106 Gr B (SA-106 B)", "ASTM A106 / ASME SA-106", "Grade B", "Tubo sem costura",
     240, 415, AC, "projectmaterials.com"),
    ("Tubos e forjados", "ASTM A53 Gr B (SA-53 B)", "ASTM A53 / ASME SA-53", "Grade B", "Tubo com e sem costura",
     240, 415, AC, "fedsteel.com"),
    ("Tubos e forjados", "ASTM A105 (SA-105)", "ASTM A105 / ASME SA-105", "", "Forjado (flanges, conexões)", 250,
     485, AC, "projectmaterials.com"),
    # inox
    ("Acos inoxidaveis", "AISI 304 (A240)", "ASTM A240 / ASME SA-240", "Type 304", "Aço inoxidável austenítico",
     205, 515, INOX, "ASTM A213/A240 via tubingchina"),
    ("Acos inoxidaveis", "AISI 304L (A240)", "ASTM A240 / ASME SA-240", "Type 304L", "Aço inoxidável austenítico",
     170, 485, INOX, "ASTM A213/A240 via tubingchina"),
    ("Acos inoxidaveis", "AISI 316 (A240)", "ASTM A240 / ASME SA-240", "Type 316", "Aço inoxidável austenítico",
     205, 515, INOX, "Rolled Alloys"),
    ("Acos inoxidaveis", "AISI 316L (A240)", "ASTM A240 / ASME SA-240", "Type 316L", "Aço inoxidável austenítico",
     170, 485, INOX316L, "Aperam (mínimos ASTM)"),
    ("Acos inoxidaveis", "AISI 430 (A240)", "ASTM A240 / ASME SA-240", "Type 430", "Aço inoxidável ferrítico",
     None, None, INOX430, ""),
    # construção mecânica (eixos, pinos, engrenagens): resistência depende do estado
    ("Acos para construcao mecanica", "SAE 1020", "SAE J403", "1020", "Aço carbono para construção mecânica",
     None, None, AC, ""),
    ("Acos para construcao mecanica", "SAE 1045", "SAE J403", "1045", "Aço carbono para construção mecânica",
     None, None, AC, ""),
    ("Acos para construcao mecanica", "SAE 4140", "SAE J404", "4140", "Aço Cr-Mo para beneficiamento", None, None,
     LIGADO, ""),
    ("Acos para construcao mecanica", "SAE 4340", "SAE J404", "4340", "Aço Ni-Cr-Mo para beneficiamento", None,
     None, LIGADO, ""),
    ("Acos para construcao mecanica", "SAE 8620", "SAE J404", "8620", "Aço Ni-Cr-Mo para cementação", None, None,
     LIGADO, ""),
    # ferro fundido
    ("Ferro fundido", "Ferro fundido cinzento FC 250", "ABNT NBR 6589", "FC 250", "Ferro fundido cinzento", None,
     None, CINZENTO, ""),
    ("Ferro fundido", "Ferro fundido nodular FE 50007", "ABNT NBR 6916", "FE 50007", "Ferro fundido nodular", None,
     None, NODULAR, ""),
    # alumínio e latão
    ("Aluminio", "Alumínio 6061-T6 (B209)", "ASTM B209", "6061-T6", "Liga de alumínio tratada", 240, 290, AL,
     "matmatch.com"),
    ("Aluminio", "Alumínio 1100-H14", "ASTM B209", "1100-H14", "Alumínio comercialmente puro (chapa lisa)", None,
     None, AL1100, ""),
    ("Aluminio", "Alumínio 5052-H32", "ASTM B209", "5052-H32", "Liga Al-Mg (chapa dobrada, naval)", None, None,
     AL5052, ""),
    ("Cobre e latao", "Latão C36000 (usinagem)", "ASTM B16", "C36000", "Latão de corte livre", None, None, LATAO,
     ""),
]


def cartao(pasta, nome, norma, grau, tipo, sy, su, base, fonte):
    u = str(uuid.uuid5(NS, nome))
    if sy:
        desc = ("Limites mínimos da especificação {}{}. Fonte da conferência: {}. Densidade, módulo de "
                "elasticidade e Poisson típicos. Confirme com o certificado do material."
                ).format(norma, (" " + grau) if grau else "", fonte)
    elif base.get("E"):
        desc = ("A resistência do {} depende do estado de fornecimento (laminado, trefilado, beneficiado) e "
                "a norma não fixa mínimo: use o valor do certificado. Densidade, módulo de elasticidade e "
                "Poisson típicos.").format(nome)
    else:
        desc = ("Densidade típica do {}. O módulo de elasticidade varia com a classe e fica a conferir; a "
                "resistência vem do certificado. Serve para massa e lista de materiais.").format(nome)
    linhas = [
        "---",
        "# Biblioteca de materiais do Prumo 3D",
        "General:",
        '  UUID: "{}"'.format(u),
        '  Author: "Prumo 3D"',
        '  License: "CC-BY-4.0"',
        '  Name: "{}"'.format(nome),
        '  Description: "{}"'.format(desc.replace('"', "'")),
        "Models:",
        "  Father:",
        "    UUID: '{}'".format(M_FATHER),
        '    Father: "Metal"',
        "  MaterialStandard:",
        "    UUID: '{}'".format(M_STD),
        '    KindOfMaterial: "{}"'.format(tipo),
        '    MaterialNumber: "{}"'.format(grau),
        '    StandardCode: "{}"'.format(norma),
    ]
    if base.get("E"):
        linhas += ["  LinearElastic:", "    UUID: '{}'".format(M_LIN),
                   '    Density: "{} kg/m^3"'.format(base["rho"]), '    PoissonRatio: "{}"'.format(base["nu"]),
                   '    YoungsModulus: "{} MPa"'.format(base["E"])]
        if sy:
            linhas.append('    YieldStrength: "{} MPa"'.format(sy))
        if su:
            linhas.append('    UltimateTensileStrength: "{} MPa"'.format(su))
    else:
        linhas += ["  Density:", "    UUID: '{}'".format(M_DENS), '    Density: "{} kg/m^3"'.format(base["rho"])]
    return "\n".join(linhas) + "\n"


def main(destino):
    # recria a biblioteca do zero (cartões que saíram da lista não ficam para trás)
    if os.path.isdir(destino):
        for nome in os.listdir(destino):
            caminho = os.path.join(destino, nome)
            if os.path.isdir(caminho):
                shutil.rmtree(caminho)
    for m in MATERIAIS:
        pasta = os.path.join(destino, m[0])
        os.makedirs(pasta, exist_ok=True)
        # O FreeCAD usa o nome do arquivo como nome do material: o arquivo leva o nome legível
        arq = re.sub(r'[\\/:*?"<>|]+', "-", m[1]) + ".FCMat"
        with open(os.path.join(pasta, arq), "w", encoding="utf-8") as f:
            f.write(cartao(*m))
    print(len(MATERIAIS), "cartões em", destino)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "src", "Mod",
                                                             "Prumo3D", "Resources", "MateriaisPrumo"))

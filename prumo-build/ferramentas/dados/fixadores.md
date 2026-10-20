# Fixadores métricos M3–M24: resumo (mm)

Os dados completos, com as fontes de cada valor, estão em `fixadores.json`.

| d | P | ISO 4017 s / k / e(A) / b(≤125)* | ISO 4762 dk / k / s / b | ISO 4032 s / m / e | ISO 7089 d1 / d2 / h |
|---|---|---|---|---|---|
| M3 | 0.5 | 5.5 / 2 / 6.01 / 12 | 5.5 / 3 / 2.5 / 18 | 5.5 / 2.4 / 6.01 | 3.2 / 7 / 0.5 |
| M4 | 0.7 | 7 / 2.8 / 7.66 / 14 | 7 / 4 / 3 / 20 | 7 / 3.2 / 7.66 | 4.3 / 9 / 0.8 |
| M5 | 0.8 | 8 / 3.5 / 8.79 / 16 | 8.5 / 5 / 4 / 22 | 8 / 4.7 / 8.79 | 5.3 / 10 / 1 |
| M6 | 1 | 10 / 4 / 11.05 / 18 | 10 / 6 / 5 / 24 | 10 / 5.2 / 11.05 | 6.4 / 12 / 1.6 |
| M8 | 1.25 | 13 / 5.3 / 14.38 / 22 | 13 / 8 / 6 / 28 | 13 / 6.8 / 14.38 | 8.4 / 16 / 1.6 |
| M10 | 1.5 | 16 / 6.4 / 17.77 / 26 | 16 / 10 / 8 / 32 | 16 / 8.4 / 17.77 | 10.5 / 20 / 2 |
| M12 | 1.75 | 18 / 7.5 / 20.03 / 30 | 18 / 12 / 10 / 36 | 18 / 10.8 / 20.03 | 13 / 24 / 2.5 |
| M16 | 2 | 24 / 10 / 26.75 / 38 | 24 / 16 / 14 / 44 | 24 / 14.8 / 26.75 | 17 / 30 / 3 |
| M20 | 2.5 | 30 / 12.5 / 33.53 / 46 | 30 / 20 / 17 / 52 | 30 / 18 / 32.95 | 21 / 37 / 3 |
| M24 | 3 | 36 / 15 / 39.98 / 54 | 36 / 24 / 19 / 60 | 36 / 21.5 / 39.55 | 25 / 44 / 4 |

\* O b vem da ISO 4014 (parafuso com rosca parcial).

## Status
- **Confirmado (2 ou mais fontes):** passo; ISO 4017/4014 (s, k, e graus A e B, b); ISO 4762 (dk, k, s); ISO 4032; ISO 7089.
- **A checar:**
  - b da ISO 4762, que vem de uma só fonte (bate com a regra 2d+12).
  - Comprimentos da ISO 4017 de M3 a M10, de uma só fonte. Os de M12 a M24 não foram levantados.
  - Valores DIN 933 e DIN 934, de uma só fonte.
  - Equivalência DIN 125-A = ISO 7089, que não foi consultada.

## DIN × ISO
- **s (DIN 933/934 × ISO 4017/4032):** M10 17 × 16; M12 19 × 18; M14 22 × 21; M22 32 × 34.
- **m da porca (DIN 934 × ISO 4032):** a ISO é mais alta. M6 5 × 5.2; M8 6.5 × 6.8; M10 8 × 8.4; M12 10 × 10.8; M16 13 × 14.8; M20 16 × 18; M24 19 × 21.5.

## Falhas de extração descartadas
| Fonte | Valor extraído | Valor adotado | Fontes do valor adotado |
|---|---|---|---|
| fasten.it ISO 4032 | m de M6 = 5 e de M24 = 19 | 5.2 e 21.5 | Torqbolt e catálogo Böllhoff |
| fasten.it ISO 4014 | e(A) de M5 = 8.87 | 8.79 | três outras fontes |
| fasten.it ISO 4017 | e(B) de M20 = 32.85 | 32.95 | duas outras fontes |

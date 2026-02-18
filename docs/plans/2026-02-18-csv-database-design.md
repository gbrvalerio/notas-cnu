# CNU B4-15-A Notas CSV Database Design

## Goal

Extract exam results from three PDF files for cargo B4-15-A (Engenheiro Agronomo - Agronomia, MDA) of the Concurso Nacional Unificado (CNU), Bloco Tematico 4, and merge them into a single CSV.

## Source Files

1. **objetiva cnu.pdf** (49MB, 5935 pages) — Objective exam results for all 87 cargos in Bloco 4. We extract only the B4-15-A section.
2. **discursiva cnu B4-15-A.pdf** — Discursive exam scores for 826 candidates.
3. **titulos cnu B4-15-A.pdf** — Title evaluation scores for 826 candidates.

## Output

`notas_b4_15_a.csv` — one row per candidate, merged by `inscricao`.

### Columns

| Column | Source | Type | Example |
|--------|--------|------|---------|
| inscricao | objetiva | string | 250000958188 |
| total_acertos | objetiva | int | 67 |
| nota_conhecimentos_gerais | objetiva | float | 20 |
| nota_conhecimentos_especificos | objetiva | float | 101 |
| nota_prova_objetiva | objetiva | float | 121 |
| situacao_prova_objetiva | objetiva | string | Aprovado |
| classificacao | objetiva | string | AC |
| nota_prova_discursiva | discursiva | float/blank | 40.75 |
| nota_titulos | titulos | float/blank | 4.00 |

### Merge Strategy

- Left join from objetiva (all B4-15-A candidates) onto discursiva and titulos by inscricao.
- Candidates not present in discursiva/titulos get blank values for those columns.

## Approach

Python script (`extract_notas.py`) using `pdftotext` (poppler) + stdlib:

1. Run `pdftotext` on each PDF to get plain text
2. Parse objetiva text: find B4-15-A section, extract candidate rows (inscricao + 6 fields)
3. Parse discursiva text: extract inscricao + nota pairs
4. Parse titulos text: extract inscricao + nota pairs
5. Merge all three by inscricao
6. Write to CSV with Portuguese headers

### Data Flow

```
objetiva cnu.pdf -> pdftotext -> parse B4-15-A section ---+
discursiva cnu B4-15-A.pdf -> pdftotext -> parse ---------+-> merge by inscricao -> notas_b4_15_a.csv
titulos cnu B4-15-A.pdf -> pdftotext -> parse -------------+
```

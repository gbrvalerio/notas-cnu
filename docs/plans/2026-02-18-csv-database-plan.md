# CNU B4-15-A CSV Database Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract exam data from three CNU PDFs for cargo B4-15-A and merge into a single CSV file.

**Architecture:** A single Python script (`extract_notas.py`) that shells out to `pdftotext` to extract text from each PDF, parses the structured text output into records, merges by inscription number, and writes a CSV. No external Python dependencies — only stdlib (`subprocess`, `csv`, `re`).

**Tech Stack:** Python 3 stdlib, `pdftotext` (poppler-utils, already installed via brew)

---

### Task 1: Create the script skeleton and objetiva parser

**Files:**
- Create: `extract_notas.py`

**Step 1: Write `extract_notas.py` with objetiva parsing**

The objetiva PDF text (via `pdftotext`) outputs data for B4-15-A as a sequence of values on separate lines, interleaved with blank lines and repeating page headers. The B4-15-A section starts after the line `(B4-15-A) Engenheiro Agrônomo - Agronomia` and ends before `(B4-16-A)`.

Each candidate record in the objetiva is 7 consecutive non-empty, non-header values:
1. inscricao (12-digit number starting with 2500)
2. total_acertos (integer)
3. nota_conhecimentos_gerais (integer)
4. nota_conhecimentos_especificos (integer)
5. nota_prova_objetiva (integer)
6. situacao (e.g. "Aprovado", "Reprovado")
7. classificacao (e.g. "AC", "PN", "PCD", "AC/PN", "Não classificado")

Page headers to skip contain: "CONCURSO PÚBLICO", "CANDIDATOS APROVADOS", "Ministério", "B4-15-A", "Inscrição", "Total de Acertos", "Nota Conhecimentos", "Gerais", "Específicos", "Nota Prova", "Objetiva (NPO)", "Situação Prova", "Objetiva", "Classificação para", "3ª e 4ª fases", "Legenda:", "Página".

```python
#!/usr/bin/env python3
"""Extract CNU B4-15-A exam results from PDFs into a merged CSV."""

import csv
import re
import subprocess
import sys


def pdftotext(pdf_path):
    """Run pdftotext and return the text output."""
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


HEADER_PATTERNS = [
    "CONCURSO PÚBLICO",
    "CANDIDATOS APROVADOS",
    "Ministério",
    "Engenheiro Agrônomo",
    "Inscrição",
    "Total de Acertos",
    "Nota Conhecimentos",
    "Gerais",
    "Específicos",
    "Nota Prova",
    "Objetiva (NPO)",
    "Situação Prova",
    "Objetiva",
    "Classificação para",
    "3ª e 4ª fases",
    "Legenda:",
    "Página",
    "B4-15-A",
    "RESULTADO DA PROVA",
    "Bloco Temático",
    "RETIFICADO",
    "Nota da Prova Discursiva",
    "Nota na Avaliação",
    "Familiar (MDA)",
    "PROVIMENTO DE VAGAS",
]


def is_header_line(line):
    """Check if a line is a repeating page header."""
    for pattern in HEADER_PATTERNS:
        if pattern in line:
            return True
    return False


def parse_objetiva(text):
    """Parse the objetiva text and return list of dicts for B4-15-A candidates."""
    # Extract B4-15-A section
    start = text.find("(B4-15-A)")
    if start == -1:
        raise ValueError("B4-15-A section not found in objetiva text")
    end = text.find("(B4-16-A)", start)
    if end == -1:
        section = text[start:]
    else:
        section = text[start:end]

    # Collect non-empty, non-header lines
    values = []
    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue
        if is_header_line(line):
            continue
        values.append(line)

    # Group into records of 7
    candidates = []
    i = 0
    while i + 6 < len(values):
        inscricao = values[i]
        if not re.match(r"^2500\d{8}$", inscricao):
            i += 1
            continue
        candidates.append({
            "inscricao": inscricao,
            "total_acertos": values[i + 1],
            "nota_conhecimentos_gerais": values[i + 2],
            "nota_conhecimentos_especificos": values[i + 3],
            "nota_prova_objetiva": values[i + 4],
            "situacao_prova_objetiva": values[i + 5],
            "classificacao": values[i + 6],
        })
        i += 7

    return candidates


def parse_simple_pdf(text):
    """Parse discursiva or titulos PDF text. Returns dict of inscricao -> nota."""
    values = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if is_header_line(line):
            continue
        values.append(line)

    result = {}
    i = 0
    while i + 1 < len(values):
        inscricao = values[i]
        if not re.match(r"^2500\d{8}$", inscricao):
            i += 1
            continue
        nota = values[i + 1].replace(",", ".")
        result[inscricao] = nota
        i += 2

    return result


def main():
    base = "."
    if len(sys.argv) > 1:
        base = sys.argv[1]

    print("Extracting objetiva...")
    objetiva_text = pdftotext(f"{base}/objetiva cnu.pdf")
    candidates = parse_objetiva(objetiva_text)
    print(f"  Found {len(candidates)} B4-15-A candidates in objetiva")

    print("Extracting discursiva...")
    discursiva_text = pdftotext(f"{base}/discursiva cnu B4-15-A.pdf")
    discursiva = parse_simple_pdf(discursiva_text)
    print(f"  Found {len(discursiva)} candidates in discursiva")

    print("Extracting titulos...")
    titulos_text = pdftotext(f"{base}/titulos cnu B4-15-A.pdf")
    titulos = parse_simple_pdf(titulos_text)
    print(f"  Found {len(titulos)} candidates in titulos")

    # Merge
    for c in candidates:
        insc = c["inscricao"]
        c["nota_prova_discursiva"] = discursiva.get(insc, "")
        c["nota_titulos"] = titulos.get(insc, "")

    # Write CSV
    output_path = f"{base}/notas_b4_15_a.csv"
    fieldnames = [
        "inscricao",
        "total_acertos",
        "nota_conhecimentos_gerais",
        "nota_conhecimentos_especificos",
        "nota_prova_objetiva",
        "situacao_prova_objetiva",
        "classificacao",
        "nota_prova_discursiva",
        "nota_titulos",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)

    print(f"Wrote {len(candidates)} rows to {output_path}")


if __name__ == "__main__":
    main()
```

**Step 2: Run the script**

Run: `python3 extract_notas.py /Volumes/development/notas-cnu`

Expected output:
```
Extracting objetiva...
  Found ~7227 B4-15-A candidates in objetiva
Extracting discursiva...
  Found 826 candidates in discursiva
Extracting titulos...
  Found 826 candidates in titulos
Wrote ~7227 rows to notas_b4_15_a.csv
```

**Step 3: Validate the output**

Verify:
- Row count matches expected (~7227 from objetiva)
- All 826 discursiva/titulos candidates are matched
- Spot-check a few known values from the PDFs
- No parsing artifacts in the data

Run: `python3 -c "import csv; rows=list(csv.DictReader(open('notas_b4_15_a.csv'))); print(f'Rows: {len(rows)}'); print(f'With discursiva: {sum(1 for r in rows if r[\"nota_prova_discursiva\"])}'); print(f'With titulos: {sum(1 for r in rows if r[\"nota_titulos\"])}'); print('First row:', rows[0]); print('Last row:', rows[-1])"`

**Step 4: Fix any parsing issues**

If the counts don't match, inspect the raw text and adjust `HEADER_PATTERNS` or parsing logic. Common issues:
- Multi-word values split across lines (e.g. "Não classificado" might be on two lines)
- Page numbers being parsed as data values

**Step 5: Commit**

```bash
git add extract_notas.py notas_b4_15_a.csv
git commit -m "feat: extract CNU B4-15-A exam results to CSV"
```

---

### Task 2: Validate data integrity

**Step 1: Cross-check counts**

```python
# Run in Python or as a script
import csv
rows = list(csv.DictReader(open("notas_b4_15_a.csv")))

# Check unique inscricao (no duplicates)
inscricoes = [r["inscricao"] for r in rows]
assert len(inscricoes) == len(set(inscricoes)), f"Duplicates found! {len(inscricoes)} vs {len(set(inscricoes))}"

# Check all discursiva/titulos candidates appear
with_disc = [r for r in rows if r["nota_prova_discursiva"]]
with_tit = [r for r in rows if r["nota_titulos"]]
print(f"Total: {len(rows)}, With discursiva: {len(with_disc)}, With titulos: {len(with_tit)}")

# Spot check: first discursiva entry should be 250000958188 with NPD 40.75
for r in rows:
    if r["inscricao"] == "250000958188":
        assert r["nota_prova_discursiva"] == "40.75", f"Expected 40.75, got {r['nota_prova_discursiva']}"
        print(f"Spot check passed: {r}")
        break
```

**Step 2: If validation passes, commit any fixes**

```bash
git add -A && git commit -m "fix: correct parsing issues found during validation"
```

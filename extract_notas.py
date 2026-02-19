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
        # Skip orphaned inscricao (next value is also an inscricao)
        if re.match(r"^2500\d{8}$", values[i + 1]):
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
        c["soma"] = float(c["nota_prova_objetiva"] or 0) + float(c["nota_prova_discursiva"] or 0) + float(c["nota_titulos"] or 0)

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
        "soma",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)

    print(f"Wrote {len(candidates)} rows to {output_path}")


if __name__ == "__main__":
    main()

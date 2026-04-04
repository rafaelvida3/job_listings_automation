def clean_single_line(text: str) -> str:
    return " ".join(text.split()).strip()


def clean_multiline_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines).strip()

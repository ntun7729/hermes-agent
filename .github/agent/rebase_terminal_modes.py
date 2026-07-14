from pathlib import Path

path = Path('apps/desktop/electron/main.ts')
text = path.read_text(encoding='utf-8')


def patch_function(name: str, old: str, new: str) -> None:
    global text
    start = text.index(f'function {name}')
    end = text.index('\n}\n', start) + 3
    segment = text[start:end]
    if old not in segment:
        raise RuntimeError(f'anchor not found in {name}')
    text = text[:start] + segment.replace(old, new, 1) + text[end:]


patch_function(
    'runRenderTitleJob',
    "      if (settled) {\n        return\n      }\n      settled = true",
    "      if (settled) {\n        return\n      }\n\n      settled = true",
)
patch_function(
    'openPortalLoginWindow',
    "      if (settled) {\n        return\n      }\n\n      settled = true",
    "      if (settled) {\n        return\n      }\n      settled = true",
)

path.write_text(text, encoding='utf-8')

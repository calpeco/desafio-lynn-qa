"""Fronteira app × test e organização do repositório."""
import re

from qa_support.paths import APP, FEATURES, ROOT, TEST


def _py(folder):
    return [p for p in folder.rglob("*.py") if "__pycache__" not in p.parts]


def test_app_nao_depende_de_test():
    """O sistema sob teste não pode importar código de teste."""
    offenders = [str(p.relative_to(ROOT)) for p in _py(APP)
                 if re.search(r"^\s*(from|import)\s+(qa_support|test\b|features|pages)", p.read_text(encoding="utf-8"), re.M)]
    assert not offenders, offenders


def test_raiz_so_tem_arquivos_transversais():
    allowed_dirs = {"app", "test", "docs", ".github", ".claude", ".venv", ".git"}
    dirs = {p.name for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith((".pytest", "__"))}
    assert dirs <= allowed_dirs, f"pastas fora do padrão na raiz: {sorted(dirs - allowed_dirs)}"
    assert not list(ROOT.glob("*.py")), "código Python solto na raiz: mova para app/ ou test/"


def test_caminhos_centralizados():
    """Só paths.py calcula a raiz; os demais usam as constantes (exceto o bootstrap que acha test/)."""
    offenders = []
    for p in _py(TEST):
        if p.name == "paths.py":
            continue
        for m in re.finditer(r"parents\[(\d)\]", p.read_text(encoding="utf-8")):
            depth_to_test = len(p.relative_to(TEST).parts) - 1
            if int(m.group(1)) != depth_to_test - 1 and int(m.group(1)) != depth_to_test:
                offenders.append(f"{p.relative_to(ROOT)} usa parents[{m.group(1)}]")
    assert not offenders, offenders


def test_features_e_steps_no_lugar_certo():
    assert (FEATURES / "environment.py").exists() and (FEATURES / "steps").is_dir() and (FEATURES / "pages").is_dir()
    assert not (ROOT / "features").exists() and not (ROOT / "tests").exists()

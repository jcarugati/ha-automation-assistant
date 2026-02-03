from pathlib import Path
import re


DIST_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "dist"


def test_dist_assets_are_relative_and_present() -> None:
    index_path = DIST_DIR / "index.html"
    assert index_path.exists(), "Expected built frontend at app/static/dist/index.html"

    html = index_path.read_text(encoding="utf-8")
    assert "/api/static/" not in html, "Dist index should not hardcode /api/static paths"

    asset_urls = re.findall(r'(?:src|href)="([^"]*assets/[^"]+)"', html)
    assert asset_urls, "Expected asset references in dist index.html"

    for url in asset_urls:
        assert not url.startswith("/"), f"Asset path should be relative: {url}"
        relative = url[2:] if url.startswith("./") else url
        asset_path = DIST_DIR / relative
        assert asset_path.exists(), f"Missing built asset: {relative}"

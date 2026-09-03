def test_secret_scan_reports_location_without_secret_value(tmp_path):
    from scripts.scan_secrets import scan_project

    source = tmp_path / "backend" / "app"
    source.mkdir(parents=True)
    secret = "sk-" + "live" + "abcdefghijklmnopqrstuv"
    (source / "unsafe.py").write_text(
        f'DEEPSEEK_API_KEY = "{secret}"\n', encoding="utf-8"
    )

    findings = scan_project(tmp_path)
    assert findings == [("backend/app/unsafe.py", 1, "openai-style-key")]
    assert secret not in repr(findings)


def test_secret_scan_allows_placeholders_and_ignores_env(tmp_path):
    from scripts.scan_secrets import scan_project

    source = tmp_path / "backend" / "app"
    source.mkdir(parents=True)
    (source / "safe.py").write_text(
        'API_KEY = "test-placeholder-value"\n', encoding="utf-8"
    )
    local_value = "real-local-" + "credential-value"
    (tmp_path / ".env").write_text(
        f'API_KEY="{local_value}"\n', encoding="utf-8"
    )
    (tmp_path / ".env.example").write_text("API_KEY=\n", encoding="utf-8")

    assert scan_project(tmp_path) == []

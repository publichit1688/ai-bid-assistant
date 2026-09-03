from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(relative_path):
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_nginx_template_enforces_https_proxy_and_upload_limit():
    content = read("deploy/nginx/ai-bid-assistant.conf.example")

    assert "listen 443 ssl" in content
    assert "client_max_body_size 50m;" in content
    assert "proxy_pass http://127.0.0.1:8000;" in content
    assert "X-Forwarded-Proto" in content
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in content
    assert "access_log off;" in content
    assert "return 301 https://" in content


def test_systemd_template_runs_precheck_and_uses_journal():
    content = read("deploy/linux/ai-bid-assistant.service.example")

    assert "ExecStartPre=" in content
    assert "start_production.py --check" in content
    assert "Restart=on-failure" in content
    assert "StandardOutput=journal" in content
    assert "NoNewPrivileges=true" in content


def test_windows_launcher_uses_existing_virtual_environment_and_precheck():
    content = read("deploy/windows/start-backend.ps1")

    assert ".venv\\Scripts\\python.exe" in content
    assert "start_production.py" in content
    assert "--check" in content
    assert "Start-Process" not in content


def test_service_template_has_restart_and_log_rotation_without_secrets():
    content = read("deploy/windows/ai-bid-assistant-service.xml.example")

    assert '<onfailure action="restart"' in content
    assert '<log mode="roll-by-size">' in content
    assert "DEEPSEEK_API_KEY" not in content
    assert "sk-" not in content


def test_release_gate_uses_a_unique_pytest_temp_directory():
    content = read("scripts/verify_release.ps1")

    assert "[guid]::NewGuid()" in content
    assert '"--basetemp=$pytestBaseTemp"' in content
    assert "--basetemp=.pytest-tmp-release" not in content
    assert "--cache-dir $pipAuditCache" in content
    assert "--cache-dir .pytest-pip-audit-cache" not in content

from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "triqee_si_chatbot.html"


def test_chat_rendering_escapes_untrusted_content_before_markdown():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "function escapeHtml(value)" in html
    assert "let html = escapeHtml(text);" in html
    assert "bubble.innerHTML" not in html
    assert "tool.textContent = toolTrace;" in html
    assert "latencyLabel.textContent = latencyStr;" in html
    assert "content.innerHTML = formatMarkdown(text);" in html


def test_crm_rendering_and_failures_do_not_create_success_shaped_fallbacks():
    html = HTML_PATH.read_text(encoding="utf-8")
    crm_section = html.split("async function submitCrmLead", 1)[1].split(
        "async function exportCrm", 1
    )[0]
    assert "resultBox.innerHTML" not in crm_section
    assert "row.textContent = line;" in crm_section
    assert "throw new Error(errors.join" in crm_section
    assert "❌ NOT PROVISIONED:" in crm_section
    assert "crypto.getRandomValues" not in crm_section

    offline_grant = html.split(
        '} else if (pLower.includes("grant")', 1
    )[1].split('} else if (pLower.includes("self-improvement")', 1)[0]
    assert "DRAFT-NOT-COMMITTED" in offline_grant
    assert "DRAFT_NOT_COMMITTED" in offline_grant
    assert "NOT PROVISIONED" in offline_grant
    assert "Math.random" not in offline_grant
    assert "successfully provisioned" not in offline_grant


def test_crm_export_requires_ephemeral_operator_key_and_has_no_dummy_data():
    html = HTML_PATH.read_text(encoding="utf-8")
    export_section = html.split("async function exportCrm", 1)[1].split(
        'window.addEventListener("DOMContentLoaded"', 1
    )[0]
    assert 'window.prompt("Enter the CRM operator key for this export:")' in export_section
    assert '"X-Admin-Key": adminKey' in export_section
    assert "localStorage" not in export_section
    assert "sessionStorage" not in export_section
    assert "dummyContent" not in export_section
    assert "CRM export failed:" in export_section


def test_offline_latency_narratives_share_one_deterministic_invariant():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "const GLOBAL_TRIANGLE_RTT_ADVANTAGE_MS = 83.56;" in html
    assert "81.44 ms" not in html
    assert html.count("GLOBAL_TRIANGLE_RTT_ADVANTAGE_MS.toFixed(2)") >= 8

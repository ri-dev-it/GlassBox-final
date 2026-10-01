from io import BytesIO
from pathlib import Path
import re
import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures/documents"


@pytest.fixture
def document_headers(client, app, tmp_path):
    app.config.update(DOCUMENT_UPLOAD_DIR=str(tmp_path), AADHAAR_HASH_KEY="test-only-secret")
    response = client.post("/api/auth/register", json={"full_name": "Asha Example", "email": "asha@example.test", "password": "strong-password-123"})
    return {"Authorization": "Bearer " + response.get_json()["token"]}


def send(client, headers, slot, filename=None):
    return client.post("/api/documents", headers=headers, data={"slot": slot,
        "file": (BytesIO((FIXTURES / (filename or f"{slot}.pdf")).read_bytes()), "upload.pdf")})


def test_wrong_slot_and_masking(client, app, document_headers):
    wrong = send(client, document_headers, "aadhaar", "salary_slip.pdf")
    assert wrong.status_code == 422
    assert wrong.json["checks"][0]["status"] == "FAIL"
    good = send(client, document_headers, "aadhaar")
    assert good.status_code == 201
    with app.app_context():
        from app.models import Document
        stored = Document.query.filter_by(
            document_type="AADHAAR_CARD"
        ).order_by(Document.id.desc()).first()
        assert Path(stored.storage_reference).read_bytes() == (
            FIXTURES / "aadhaar.pdf"
        ).read_bytes()


@pytest.mark.parametrize(('slot', 'confidence'), [('aadhaar', 0.56), ('pan', 0.57)])
def test_same_type_marker_is_accepted(client, document_headers, monkeypatch, slot, confidence):
    from app.services import document_pipeline
    monkeypatch.setattr(document_pipeline, 'obvious_document_type', lambda _: slot)
    response = send(client, document_headers, slot)
    assert response.status_code == 201
    type_check = next(c for c in response.json['checks'] if c['name'] == 'document_type')
    assert type_check['status'] == 'PASS'
    assert type_check['evidence']['detected'] != 'unknown'
    assert 'Wrong document type' not in type_check['reason']


def test_ocr_field_parser_accepts_common_recognition_punctuation():
    from app.services.document_pipeline import field
    assert field('Name Asha Example', 'name') == 'Asha Example'
    assert field('DOB; 15/01/1995', r'dob|date of birth') == '15/01/1995'


def test_ocr_diagnostics_are_redacted_and_opt_in(app, caplog):
    from app.services.document_pipeline import _log_ocr_diagnostics
    app.config['DOCUMENT_OCR_DIAGNOSTICS'] = True
    private_text = (
        'Government of India\nUnique Identification Authority\n'
        'Name: Private Person\nDOB: 15/01/1995\n999988887779'
    )
    with app.app_context():
        _log_ocr_diagnostics(
            private_text, 'aadhaar',
            {'name': 'Private Person', 'dob': '15/01/1995'}, 'aadhaar',
        )
    assert 'government_marker=True' in caplog.text
    assert 'authority_marker=True' in caplog.text
    assert 'name_label=True' in caplog.text
    assert 'dob_label=True' in caplog.text
    assert 'Private Person' not in caplog.text
    assert '15/01/1995' not in caplog.text
    assert '999988887779' not in caplog.text


def test_raw_ocr_debug_capture_is_private_and_opt_in(app, tmp_path, caplog):
    from app.services.document_pipeline import _save_raw_ocr_debug
    app.config.update(
        DOCUMENT_UPLOAD_DIR=str(tmp_path), DOCUMENT_OCR_RAW_DEBUG=True
    )
    raw_text = 'Government of India\nName: Private Person\n1234 5678 9012'
    with app.app_context():
        path = _save_raw_ocr_debug(raw_text, 'aadhaar')
    assert path.parent == tmp_path / 'ocr-debug'
    assert path.read_text(encoding='utf-8') == raw_text
    assert 'Private Person' not in caplog.text
    assert str(path) in caplog.text

    app.config['DOCUMENT_OCR_RAW_DEBUG'] = False
    with app.app_context():
        assert _save_raw_ocr_debug(raw_text, 'pan') is None


def test_pan_cannot_pass_aadhaar_slot_even_with_aadhaar_filename(client, document_headers):
    response = client.post('/api/documents', headers=document_headers, data={
        'documentType': 'AADHAAR_CARD', 'confirmedDocumentType': 'true',
        'file': (BytesIO((FIXTURES / 'pan.pdf').read_bytes()), 'aadhaar.pdf'),
    })
    assert response.status_code == 422
    assert response.json['document']['status'] == 'REJECTED'
    checks = {check['name']: check['status'] for check in response.json['checks']}
    assert checks['document_type'] == 'FAIL'
    assert 'aadhaar_checksum' not in checks
    assert 'aadhaar_markers' not in checks


@pytest.mark.parametrize('variant', ['Government of India', 'Unique Identification Authority', 'checksum'])
def test_aadhaar_marker_and_checksum_fields_do_not_block_upload(client, document_headers, variant):
    from reportlab.pdfgen import canvas
    from tests.fixtures.generate_documents import sample_texts
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    text = sample_texts()['aadhaar']
    if variant == 'checksum':
        number = re.search(r'\b\d{12}\b', text).group()
        replacement = number[:-1] + ('0' if number[-1] != '0' else '1')
        text = text.replace(number, replacement)
    else:
        text = text.replace(variant, '')
    for index, line in enumerate(text.splitlines()):
        pdf.drawString(40, 800 - index * 22, line)
    pdf.save()
    response = client.post('/api/documents', headers=document_headers, data={
        'slot': 'aadhaar', 'file': (BytesIO(buffer.getvalue()), 'aadhaar.pdf'),
    })
    assert response.status_code == 201
    assert response.json['document']['status'] == 'UPLOADED'
    checks = {check['name'] for check in response.json['checks']}
    assert 'aadhaar_checksum' not in checks
    assert 'aadhaar_markers' not in checks


def test_aadhaar_accepts_issuer_and_dob_ocr_punctuation(client, document_headers):
    from reportlab.pdfgen import canvas
    from tests.fixtures.generate_documents import sample_texts
    text = (
        sample_texts()['aadhaar']
        .replace('Government of India', 'Government, of India')
        .replace('Unique Identification Authority', 'Unique: Identification Authority')
        .replace('DOB:', 'DOB;')
    )
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for index, line in enumerate(text.splitlines()):
        pdf.drawString(40, 800 - index * 22, line)
    pdf.save()
    response = client.post('/api/documents', headers=document_headers, data={
        'slot': 'aadhaar', 'file': (BytesIO(buffer.getvalue()), 'aadhaar.pdf'),
    })
    assert response.status_code == 201, response.json
    checks = {item['name']: item['status'] for item in response.json['checks']}
    assert checks['identity_name'] == 'PASS'
    extracted = response.json['document']['verification']['extractedInformation']
    assert extracted['name'] == 'Asha Example'
    assert extracted['dob'] == '1995-01-15'


def test_aadhaar_missing_dob_is_review_not_upload_rejection(client, document_headers):
    from reportlab.pdfgen import canvas
    from tests.fixtures.generate_documents import sample_texts
    text = sample_texts()['aadhaar'].replace('DOB: 1995-01-15\n', '')
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for index, line in enumerate(text.splitlines()):
        pdf.drawString(40, 800 - index * 22, line)
    pdf.save()
    response = client.post('/api/documents', headers=document_headers, data={
        'slot': 'aadhaar', 'file': (BytesIO(buffer.getvalue()), 'aadhaar.pdf'),
    })
    assert response.status_code == 201
    assert response.json['document']['status'] == 'UPLOADED'
    assert response.json['document']['verification']['extractedInformation']['dob'] is None


def test_pan_identifier_extraction_failure_is_review_not_upload_rejection(client, document_headers, monkeypatch):
    from app.services import document_pipeline
    from tests.fixtures.generate_documents import sample_texts
    text = sample_texts()['pan'].replace('ABCDE1234F', '')
    monkeypatch.setattr(document_pipeline, 'extract', lambda *_: (text, {}, []))
    monkeypatch.setattr(document_pipeline, 'obvious_document_type', lambda _: 'pan')
    response = send(client, document_headers, 'pan')
    assert response.status_code == 201
    pan_format = next(c for c in response.json['checks'] if c['name'] == 'pan_format')
    assert pan_format['status'] == 'WARN'


def test_upload_requires_auth_and_real_content(client, document_headers):
    assert send(client, {}, "aadhaar").status_code == 401
    response = client.post("/api/documents", headers=document_headers,
        data={"slot": "aadhaar", "file": (BytesIO(b"not a pdf"), "x.pdf")})
    assert response.status_code == 400


def test_identity_mismatch_and_reuse(client, app, document_headers):
    assert send(client, document_headers, "aadhaar").status_code == 201
    wrong = send(client, document_headers, "salary_slip", "mismatched_salary.pdf")
    assert wrong.status_code == 201
    assert wrong.json['document']['status'] == 'UPLOADED'
    assert any(c["name"] == "identity_name" and c["status"] == "WARN" for c in wrong.json["checks"])
    response = client.post("/api/auth/register", json={"full_name": "Asha Example", "email": "another@example.test", "password": "strong-password-123"})
    other = {"Authorization": "Bearer " + response.json["token"]}
    # Identical/same-identity uploads are permitted in the demo workflow.
    reused = client.post('/api/documents', headers=other, data={'slot': 'aadhaar',
        'file': (BytesIO((FIXTURES / 'aadhaar.pdf').read_bytes() + b'\n%different serialization\n'), 'identity.pdf')})
    assert reused.status_code == 201
    assert all(c['name'] != 'reuse' for c in reused.json['checks'])
    with app.app_context():
        from app.models import VerificationReport
        assert VerificationReport.query.count() == 3
    copied = send(client, other, 'salary_slip', 'mismatched_salary.pdf')
    assert copied.status_code == 201
    assert any(c['name'] == 'identity_name' and c['status'] == 'WARN' for c in copied.json['checks'])


@pytest.mark.parametrize("decision,verdict,expected", [("APPROVE", "REJECTED", "REVIEW"),
    ("APPROVE", "NEEDS_REVIEW", "REVIEW"), ("DECLINE", "NEEDS_REVIEW", "DECLINE"),
    ("APPROVE", "VERIFIED", "APPROVE"), ("REVIEW", "REJECTED", "REVIEW")])
def test_decision_policy(decision, verdict, expected):
    from app.services.document_pipeline import apply_verdict
    assert apply_verdict(decision, verdict) == expected


def test_transaction_risk_factors_can_drive_decline_with_named_reasons():
    from app.services.application_service import apply_bank_transaction_evidence
    features = {
        'avg_monthly_credits': 45000,
        'salary_regularity': 1,
        'avg_monthly_balance': 2000,
        'min_monthly_balance': -500,
        'emi_debit_count': 3,
        'emi_debit_share': 0.7,
        'fixed_obligation_to_income_ratio': 0.7,
        'bounced_payment_count': 1,
        'cash_withdrawal_share': 0.8,
        'negative_balance_days': 3,
        'transaction_velocity': 2,
        'income_volatility': 0.8,
    }
    result, reasoning = apply_bank_transaction_evidence(
        {'prediction': 'APPROVE', 'probability': 0.65},
        features,
        {'start': '2026-01-01', 'end': '2026-03-31', 'observed_days': 90},
    )
    assert result['prediction'] == 'DECLINE'
    assert result['probability'] < 0.45
    assert {'negative_balance_days', 'salary_regularity', 'income_volatility'} <= {
        factor['feature'] for factor in reasoning['factors']
    }
    assert '3 day(s) had a negative balance' in reasoning['summary']
    assert 'Monthly credit volatility' in reasoning['summary']


def test_report_auth_and_complete_documents(client, document_headers):
    assert client.get('/api/documents/report').status_code == 401
    for slot in ('aadhaar', 'pan', 'salary_slip', 'bank_statement'):
        assert send(client, document_headers, slot).status_code == 201
    report = client.get('/api/documents/report', headers=document_headers)
    assert report.json['verdict'] == 'VERIFIED'
    assert report.json['features']['avg_monthly_credits'] == 45000


def test_csv_transactions_persist(client, app, document_headers):
    text = 'Bank Statement\nAccount holder: Asha Example\nAccount number: 12345678\nIFSC: DEMO0000001\ndate,description,debit,credit,balance\n2026-01-01,Salary,0,45000,45000\n2026-01-02,EMI,5000,0,40000\n'
    response = client.post('/api/documents', headers=document_headers, data={'slot': 'bank_statement', 'file': (BytesIO(text.encode()), 'statement.csv')})
    assert response.status_code == 201
    with app.app_context():
        from app.models import DocumentTransaction
        assert DocumentTransaction.query.count() == 2


def test_submission_override_snapshot_and_report_privacy(client, app, document_headers, monkeypatch):
    from app.services import application_service as service
    from app.models import User, Document
    for slot in ('aadhaar', 'pan', 'salary_slip'):
        assert send(client, document_headers, slot).status_code == 201
    statement = (
        'Bank Statement\nAccount holder: Asha Example\n'
        'Account number: 12345678\nIFSC: DEMO0000001\n'
        'date,description,debit,credit,balance\n'
        '2026-01-01,Opening,0,0,10000\n'
            '2026-01-05,Salary Example Labs,0,45000,55000\n'
            '2026-02-05,Salary Example Labs,0,45000,100000\n'
            '2026-03-05,Salary Example Labs,0,45000,145000\n'
            '2026-04-01,Salary Example Labs,0,45000,190000\n'
    )
    bank_upload = client.post('/api/documents', headers=document_headers, data={
        'slot': 'bank_statement', 'file': (BytesIO(statement.encode()), 'bank.csv'),
    })
    assert bank_upload.status_code == 201
    monkeypatch.setattr(service.ab_test_service, 'get_assignment', lambda _: None)
    model_inputs = {}
    def predict(features):
        model_inputs.update(features)
        return {'prediction': 'APPROVE', 'probability': 0.95}
    monkeypatch.setattr(service.ml_service, 'predict_application', predict)
    monkeypatch.setattr(service.ml_service, 'get_model_metadata', lambda: {'final_model': 'test'})
    for method in ('get_shap_explanation', 'get_lime_explanation'):
        monkeypatch.setattr(service.ml_service, method, lambda *args: {'contributions': [], 'plain_english': 'Model explanation.'})
    monkeypatch.setattr(service.ml_service, 'get_shap_lime_comparison', lambda *args: {})
    with app.app_context():
        user = User.query.filter_by(email='asha@example.test').one()
        result = service.submit_application(user, {})
        application_id = result['application']['id']
        assert result['prediction']['decision'] == 'APPROVE'
        assert model_inputs['avg_monthly_credits'] == 45000
        assert model_inputs['salary_regularity'] == 4
        assert result['transactionReasoning']['factors']
        assert result['transactionReasoning']['adjustedApprovalProbability'] > 0.95
        assert 'Consistent salary credits' in result['shap']['plain_english']
        assert len(result['documentVerification']['bankStatement']['transactions']) == 4
        identity = Document.query.filter_by(document_type='AADHAAR_CARD').first()
        assert Path(identity.storage_reference).read_bytes() == (
            FIXTURES / 'aadhaar.pdf'
        ).read_bytes()
    saved = client.get(f'/api/documents/applications/{application_id}/report', headers=document_headers)
    assert saved.json['verdict'] == 'VERIFIED'
    assert send(client, document_headers, 'salary_slip', 'mismatched_salary.pdf').status_code == 201
    # Re-uploading for a new application must not mutate the submitted snapshot.
    send(client, document_headers, 'aadhaar')
    assert client.get(f'/api/documents/applications/{application_id}/report', headers=document_headers).json == saved.json
    other = client.post('/api/auth/register', json={'full_name': 'Other Person', 'email': 'other@example.test', 'password': 'strong-password-123'})
    headers = {'Authorization': 'Bearer ' + other.json['token']}
    assert client.get(f'/api/documents/applications/{application_id}/report', headers=headers).status_code == 404


def test_invalid_slot_and_size_but_not_checksum(client, app, document_headers):
    assert send(client, document_headers, 'unknown', 'aadhaar.pdf').status_code == 400
    app.config['MAX_DOCUMENT_SIZE_BYTES'] = 10
    assert send(client, document_headers, 'aadhaar').status_code == 400
    app.config['MAX_DOCUMENT_SIZE_BYTES'] = 5 * 1024 * 1024
    response = send(client, document_headers, 'aadhaar', 'invalid_aadhaar.pdf')
    assert response.status_code == 201
    assert response.json['document']['status'] == 'UPLOADED'


@pytest.mark.parametrize('loan_type', ['PERSONAL_LOAN', 'CAR_LOAN', 'BIKE_LOAN', 'HOME_LOAN', 'BUSINESS_CAPITAL', 'EDUCATION_LOAN'])
def test_all_loan_types_require_documents_before_model(client, app, document_headers, monkeypatch, loan_type):
    from tests.backend.test_analysis_flow import _ui_payload
    from app.services import ml_service
    from app.models import Application
    def unexpected(*args):
        pytest.fail('Model must not run before mandatory document validation')
    monkeypatch.setattr(ml_service, 'predict_application', unexpected)
    response = client.post('/api/predict', headers=document_headers, json=_ui_payload(loan_type=loan_type))
    assert response.status_code == 422
    assert len(response.json['errors']) == 4
    assert any('PAN Card' in error for error in response.json['errors'])
    with app.app_context():
        assert Application.query.count() == 0


def test_pan_slot_type_validation_and_retired_type(client, document_headers):
    for slot in ('aadhaar', 'salary_slip', 'bank_statement'):
        assert send(client, document_headers, slot).status_code == 201
    assert client.get('/api/documents/report', headers=document_headers).json['canSubmit'] is False
    wrong = send(client, document_headers, 'pan', 'salary_slip.pdf')
    assert wrong.status_code == 422
    assert client.get('/api/documents/report', headers=document_headers).json['canSubmit'] is False
    assert send(client, document_headers, 'pan').status_code == 201
    report = client.get('/api/documents/report', headers=document_headers).json
    assert report['canSubmit'] is True
    assert report['verdict'] == 'VERIFIED'
    assert all(c['slot'] != 'income_certificate' and c['name'] != 'annual_income' for c in report['checks'])
    assert send(client, document_headers, 'income_certificate', 'salary_slip.pdf').status_code == 400
    response = client.post('/api/documents', headers=document_headers, data={'documentType': 'EMPLOYMENT_INCOME_PROOF', 'file': (BytesIO(b'dummy'), 'old.pdf')})
    assert response.status_code == 400


@pytest.mark.parametrize('wrong', [False, True])
def test_remove_accepted_and_rejected_slot(client, app, document_headers, wrong):
    from app.models import Document, DocumentAudit, VerificationReport
    uploaded = send(client, document_headers, 'aadhaar', 'salary_slip.pdf' if wrong else 'aadhaar.pdf')
    document_id = uploaded.json['document']['id']
    with app.app_context():
        path = Path(Document.query.get(document_id).storage_reference)
        assert path.exists()
    deleted = client.delete(f'/api/documents/{document_id}', headers=document_headers)
    assert deleted.status_code == 200, deleted.json
    assert not path.exists()
    assert deleted.json['report']['identity'] == {}
    assert deleted.json['report']['canSubmit'] is False
    with app.app_context():
        assert DocumentAudit.query.count() == 0
        assert Document.query.count() == 0
        assert VerificationReport.query.count() == 1
    assert send(client, document_headers, 'aadhaar').status_code == 201


def test_remove_bank_versions_and_extraction(client, app, document_headers):
    from app.models import Document, DocumentTransaction, DocumentAudit
    for _ in range(2):
        response = send(client, document_headers, 'bank_statement')
    with app.app_context():
        paths = [Path(d.storage_reference) for d in Document.query.all()]
        assert DocumentTransaction.query.count() == 10
    removed = client.delete(f"/api/documents/{response.json['document']['id']}", headers=document_headers)
    assert removed.status_code == 200
    assert removed.json['report']['bankStatement'] is None
    assert removed.json['report']['features'] == {}
    assert all(not path.exists() for path in paths)
    with app.app_context():
        assert DocumentTransaction.query.count() == 0
        assert DocumentAudit.query.count() == 0
    assert client.get('/api/documents/pending', headers=document_headers).json['documents'] == []


def test_remove_auth_and_review_locks(client, app, document_headers):
    from app.models import Document, User, Applicant, Application
    from app.extensions import db
    response = send(client, document_headers, 'aadhaar')
    document_id = response.json['document']['id']
    url = f'/api/documents/{document_id}'
    assert client.delete(url).status_code == 401
    other = client.post('/api/auth/register', json={'full_name': 'Other Person', 'email': 'other@example.test', 'password': 'strong-password-123'})
    assert client.delete(url, headers={'Authorization': 'Bearer ' + other.json['token']}).status_code == 404
    with app.app_context():
        doc = db.session.get(Document, document_id)
        path = Path(doc.storage_reference)
        doc.document_status = 'approved'
        db.session.commit()
    assert client.delete(url, headers=document_headers).status_code == 409
    with app.app_context():
        user = User.query.filter_by(email='asha@example.test').one()
        applicant = Applicant(user_id=user.id, full_name=user.full_name)
        db.session.add(applicant); db.session.flush()
        application = Application(applicant_id=applicant.id, features_json='{}', admin_decision='APPROVE')
        db.session.add(application); db.session.flush()
        db.session.get(Document, document_id).application_id = application.id
        db.session.commit()
    assert client.delete(url, headers=document_headers).status_code == 409
    assert path.exists()


@pytest.mark.parametrize('name,status', [('Asha Example', 'PASS'), ('Rohan Different', 'WARN'), ('', 'WARN')])
def test_bank_header_identity_and_private_transactions(client, document_headers, name, status):
    send(client, document_headers, 'aadhaar')
    text = f'Bank Statement\nAccount holder name: {name}\nAccount number: 9876543210\nBank name: Example Bank\nBranch: Central\nIFSC: DEMO0000001\ndate,description,debit,credit,balance\n2026-01-01,Salary,0,45000,45000\n2026-01-02,EMI,5000,0,40000\n'
    response = client.post('/api/documents', headers=document_headers, data={'slot': 'bank_statement', 'file': (BytesIO(text.encode()), 'bank.csv')})
    assert response.status_code == 201
    report = client.get('/api/documents/report', headers=document_headers).json
    identity = next(c for c in report['checks'] if c['slot'] == 'bank_statement' and c['name'] == 'identity_name')
    assert identity['status'] == status
    details = report['bankStatement']
    assert details['accountHolder'] == (name or None)
    assert details['accountNumber'] == '******3210'
    assert details['bankName'] == 'Example Bank'
    assert details['branch'] == 'Central'
    assert details['ifsc'] == 'DEMO0000001'
    assert len(details['transactions']) == 2
    if status == 'WARN':
        assert 'administrator review is recommended' in identity['reason'].lower()
    assert '9876543210' not in str(report)
    url = f"/api/documents/{response.json['document']['id']}/bank-statement"
    assert client.get(url, headers=document_headers).json == details
    assert client.get(url).status_code == 401
    other = client.post('/api/auth/register', json={'full_name': 'Other', 'email': 'bank-other@example.test', 'password': 'strong-password-123'})
    assert client.get(url, headers={'Authorization': 'Bearer ' + other.json['token']}).status_code == 404


def test_bank_zero_transactions(client, document_headers):
    text = 'Bank Statement\nAccount holder: Asha Example\nAccount number: 12345678\nIFSC: DEMO0000001\ndate,description,debit,credit,balance\n'
    response = client.post('/api/documents', headers=document_headers, data={'slot': 'bank_statement', 'file': (BytesIO(text.encode()), 'bank.csv')})
    assert response.status_code == 201
    details = client.get('/api/documents/report', headers=document_headers).json['bankStatement']
    assert details['transactions'] == []
    assert any(c['name'] == 'bank_transactions' and c['status'] == 'FAIL' for c in client.get('/api/documents/report', headers=document_headers).json['checks'])


@pytest.mark.parametrize(('slot', 'filename', 'expected', 'detected'), [
    ('aadhaar', 'pan.pdf', 'Aadhaar', 'PAN Card'),
    ('pan', 'salary_slip.pdf', 'PAN Card', 'Salary slip'),
    ('salary_slip', 'bank_statement.pdf', 'Salary slip', 'Bank statement'),
    ('bank_statement', 'pan.pdf', 'Bank statement', 'PAN Card'),
])
def test_every_slot_rejects_wrong_classified_type(client, document_headers, slot, filename, expected, detected):
    response = send(client, document_headers, slot, filename)
    assert response.status_code == 422
    document_type = next(check for check in response.json['checks'] if check['name'] == 'document_type')
    assert document_type['status'] == 'FAIL'
    assert f'Wrong document type: expected {expected}; detected {detected}' in document_type['reason']


@pytest.mark.parametrize('slot', ['aadhaar', 'pan', 'salary_slip', 'bank_statement'])
def test_every_slot_flags_a_different_account_holder_for_review(client, app, slot, tmp_path):
    app.config.update(DOCUMENT_UPLOAD_DIR=str(tmp_path), AADHAAR_HASH_KEY='test-only-secret')
    registered = client.post('/api/auth/register', json={
        'full_name': 'Applicant Owner', 'email': 'owner@example.test',
        'password': 'strong-password-123',
    })
    headers = {'Authorization': 'Bearer ' + registered.json['token']}
    response = send(client, headers, slot)
    assert response.status_code == 201
    assert response.json['document']['status'] == 'UPLOADED'
    identity = next(check for check in response.json['checks'] if check['name'] == 'identity_name')
    assert identity['status'] == 'WARN'
    assert identity['reason'].endswith('administrator review is recommended.')


def test_bank_statement_only_stores_latest_ninety_days(client, document_headers):
    text = (
        'Bank Statement\nAccount holder: Asha Example\n'
        'Account number: 12345678\nIFSC: DEMO0000001\n'
        'date,description,debit,credit,balance\n'
        '2026-01-01,Opening,0,0,10000\n'
        '2026-01-05,Salary,0,45000,55000\n'
        '2026-02-05,Salary,0,45000,100000\n'
        '2026-03-05,Salary,0,45000,145000\n'
        '2026-04-01,Salary,0,45000,190000\n'
    )
    response = client.post('/api/documents', headers=document_headers, data={
        'slot': 'bank_statement', 'file': (BytesIO(text.encode()), 'statement.csv'),
    })
    assert response.status_code == 201
    details = client.get('/api/documents/report', headers=document_headers).json['bankStatement']
    assert [row['date'] for row in details['transactions']] == [
        '2026-01-05', '2026-02-05', '2026-03-05', '2026-04-01',
    ]
    assert details['period']['observed_days'] == 87
    assert details['features']['salary_regularity'] == 4

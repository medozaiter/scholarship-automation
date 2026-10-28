import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
import time
from fastapi.testclient import TestClient
from web.app import app
from services.security_utils import validate_gpa, validate_name, validate_email, validate_talents_experience
from services.advisor_service import AdvisorService

client = TestClient(app)
advisor_service = AdvisorService()

def test_security_input_filters():
    print("[TEST 1] Testing Strict Security Input Filters...")
    
    # Valid GPAs
    assert validate_gpa("88%") == "88%"
    assert validate_gpa("3.75") == "3.75/4"
    assert validate_gpa("95.5") == "95.5%"
    
    # Reject letters or scripts in GPA
    try:
        validate_gpa("<script>alert(1)</script>")
        assert False, "Should reject script in GPA"
    except ValueError:
        pass

    try:
        validate_gpa("معدل ممتاز 90")
        assert False, "Should reject arabic letters in GPA"
    except ValueError:
        pass

    # Validate Name
    assert validate_name("مصطفى زعيتر") == "مصطفى زعيتر"
    try:
        validate_name("Student<script>")
        assert False, "Should reject script in name"
    except ValueError:
        pass

    # Validate Talents
    clean_talents = validate_talents_experience("مشارك في هاكاثون فلسطين، متطوع في الإغاثة الطبية")
    assert "هاكاثون" in clean_talents
    
    print(" -> PASSED: Strict Input Filters block scripts and letters in numeric fields.")

def test_admission_probability():
    print("[TEST 2] Testing Admission Probability Calculation...")
    res = advisor_service.calculate_match_score(
        gpa="92%",
        majors=["Software Engineering"],
        country="Palestine",
        scholarship={"name": "Lester B. Pearson", "target_majors": ["Software Engineering"]},
        student_talents="الفوز بالمركز الأول في هاكاثون غزة للذكاء الاصطناعي وبحث منشور"
    )
    assert "admission_probability" in res
    assert "%" in res["admission_probability"]
    assert len(res["strengths"]) > 0
    print(f" -> PASSED: Admission probability calculated: {res['admission_probability']}, Score: {res['match_score']}")

def test_live_scholarships_endpoint():
    print("[TEST 3] Testing /api/scholarships/live Endpoint...")
    resp = client.get("/api/scholarships/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] >= 5
    assert len(data["scholarships"]) >= 5
    first = data["scholarships"][0]
    assert "name" in first
    assert "official_link" in first
    print(f" -> PASSED: Retrieved {data['count']} automated live scholarships.")

def test_interactive_advisor_chat():
    print("[TEST 4] Testing /api/advisor/chat Endpoint...")
    resp = client.post("/api/advisor/chat", json={
        "query": "معدلي 85 وهندسة برمجيات وبدي منحة في أوروبا شو بتنصحني؟",
        "email": "medo.msz.2006@gmail.com",
        "history": []
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "advice" in data
    assert len(data["advice"]) > 30
    print(f" -> PASSED: Advisor returned concise advice ({len(data['advice'])} chars).")

def test_document_download_with_letterhead():
    print("[TEST 5] Testing /api/documents/download with Official Letterhead...")
    resp = client.post("/api/documents/download", json={
        "student_name": "Mustafa AbuZaiter",
        "email": "medo.msz.2006@gmail.com",
        "degree": "Undergraduate",
        "major": "Cybersecurity",
        "gpa": "90%",
        "scholarship_name": "Stipendium Hungaricum",
        "doc_type": "motivation",
        "talents_experience": "Cybersecurity CTF champion, volunteer",
        "send_to_email": False
    })
    assert resp.status_code == 200
    text = resp.text
    assert "SCHOLARPILOT AI ACADEMIC DOSSIER" in text
    assert "REF ID:" in text
    assert "Mustafa AbuZaiter" in text
    print(" -> PASSED: Downloadable document with official institutional letterhead generated successfully.")

def test_subscription_automation():
    print("[TEST 6] Testing Student Subscription & Profile Update...")
    unique_email = f"student_{int(time.time())}@example.com"
    resp = client.post("/api/subscribe", json={
        "email": unique_email,
        "full_name": "Ahmad Test",
        "degree": "Undergraduate (Bachelor's)",
        "majors": ["Artificial Intelligence", "Computer Science"],
        "gpa": "91%",
        "talents_experience": "Participated in NASA Space Apps, active volunteer",
        "country": "Palestine",
        "send_welcome_report": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["subscriber"]["email"] == unique_email
    print(" -> PASSED: Subscription saved with talents and automatic tracking enabled.")

if __name__ == "__main__":
    test_security_input_filters()
    test_admission_probability()
    test_live_scholarships_endpoint()
    test_interactive_advisor_chat()
    test_document_download_with_letterhead()
    test_subscription_automation()
    print("\nALL AUTOMATION AND SECURITY TESTS PASSED PERFECTLY!")

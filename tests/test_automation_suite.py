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
    assert validate_name("أحمد محمود") == "أحمد محمود"
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

def test_subscription_automation():
    print("[TEST 5] Testing Student Weekly Subscription & Profile Update...")
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
    print(" -> PASSED: Subscription saved with talents and automatic weekly tracking enabled.")

def test_ai_advisor_suite():
    print("[TEST 6] Testing AI Advisor Production Suite Endpoints...")
    
    # 1. Acceptance Chance Estimator
    chances_resp = client.post("/api/advisor/chances", json={
        "scholarship_name": "Lester B. Pearson",
        "email": "medo.msz.2006@gmail.com"
    })
    assert chances_resp.status_code == 200
    chances_data = chances_resp.json()
    assert "chance_percentage" in chances_data
    assert "competitiveness" in chances_data
    assert "strengths" in chances_data
    print(f" -> PASSED: Chances Estimator ({chances_data['chance_percentage']}%)")

    # 2. Scholarship Comparison
    compare_resp = client.post("/api/advisor/compare", json={
        "scholarships": ["Lester B. Pearson", "Chevening UK Government Scholarship"],
        "email": "medo.msz.2006@gmail.com"
    })
    assert compare_resp.status_code == 200
    compare_data = compare_resp.json()
    assert "comparison_table" in compare_data
    assert len(compare_data["comparison_table"]) == 2
    assert "verdict" in compare_data
    print(f" -> PASSED: Scholarship Comparison ({len(compare_data['comparison_table'])} scholarships compared)")

    # 3. CV Reviewer
    cv_resp = client.post("/api/advisor/review-cv", json={
        "cv_text": "Experienced software developer, BSc Computer Science with 89% GPA. Led AI research projects. Fluent in English.",
        "target_scholarship": "DAAD Germany"
    })
    assert cv_resp.status_code == 200
    cv_data = cv_resp.json()
    assert "cv_score" in cv_data
    assert "recommendations" in cv_data
    print(f" -> PASSED: CV Reviewer (Score: {cv_data['cv_score']}/100)")

    # 4. Motivation Letter Reviewer
    letter_resp = client.post("/api/advisor/review-letter", json={
        "letter_text": "I am applying for the master's degree in AI. Throughout my academic career I have developed multiple high-impact projects.",
        "scholarship_name": "Chevening"
    })
    assert letter_resp.status_code == 200
    letter_data = letter_resp.json()
    assert "letter_score" in letter_data
    assert "missing_sections" in letter_data
    print(f" -> PASSED: Letter Reviewer (Score: {letter_data['letter_score']}/100)")

    # 5. Application Roadmap
    roadmap_resp = client.post("/api/advisor/roadmap", json={
        "scholarship_name": "Stipendium Hungaricum",
        "weeks": 4
    })
    assert roadmap_resp.status_code == 200
    roadmap_data = roadmap_resp.json()
    assert "weeks" in roadmap_data
    assert "checklist" in roadmap_data
    assert len(roadmap_data["weeks"]) == 4
    print(f" -> PASSED: Application Roadmap ({len(roadmap_data['weeks'])} weeks generated)")

    # 6. Email Assistant
    email_resp = client.post("/api/advisor/draft-email", json={
        "email_type": "professor_outreach",
        "recipient_name": "Dr. Sarah Adams",
        "scholarship_name": "DAAD",
        "field": "Artificial Intelligence"
    })
    assert email_resp.status_code == 200
    email_data = email_resp.json()
    assert "subject" in email_data
    assert "body" in email_data
    print(f" -> PASSED: Email Assistant (Drafted: '{email_data['subject']}')")

    # 7. Deadline Analytics
    dl_resp = client.get("/api/advisor/deadlines")
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()
    assert "closing_this_week" in dl_data
    assert "closing_in_30_days" in dl_data
    print(f" -> PASSED: Deadline Analytics (Active: {dl_data['total_active']})")

if __name__ == "__main__":
    test_security_input_filters()
    test_admission_probability()
    test_live_scholarships_endpoint()
    test_interactive_advisor_chat()
    test_subscription_automation()
    test_ai_advisor_suite()
    print("\nALL AUTOMATION AND SECURITY TESTS PASSED PERFECTLY!")

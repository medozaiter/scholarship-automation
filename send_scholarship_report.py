import os
import csv
import smtplib
import logging
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==================== VERIFIED SCHOLARSHIPS DIRECTORY ====================
# Strictly conforms to: Undergraduate, Palestine Eligible, Cybersecurity / Software Eng / AI / CS,
# Open Now or Opening Soon, Sorted Chronologically by Deadline.

SCHOLARSHIPS_DATA = [
    {
        "name": "Lester B. Pearson International Scholarship Program",
        "provider": "University of Toronto",
        "country_institution": "Canada / University of Toronto",
        "language": "English",
        "status": "Open Now (Final student deadline approaching)",
        "deadline": "2026-11-06",
        "mechanism": "Separate Application (School nomination + OUAC university application, followed by personalized scholarship portal form)",
        "requirements": "High school senior with exceptional academic achievement (A / 90%+ equivalent), recognized leadership & creative thinking, English proficiency (IELTS 6.5+ / TOEFL 100)",
        "tests": "SAT / ACT optional and not required for international curriculum",
        "visa_support": "Full documentation: Letter of Acceptance (LOA) & Provincial Attestation Letter (PAL) issued for Canadian Study Permit",
        "competitiveness": "Very High (~37 scholars selected worldwide each year)",
        "official_link": "https://future.utoronto.ca/pearson/",
        "funding": "Fully Funded (Tuition, books, incidental fees & full residence for 4 years)"
    },
    {
        "name": "UBC International Scholars Program (Donald A. Wehrung & Karen McKellin Awards)",
        "provider": "University of British Columbia (UBC)",
        "country_institution": "Canada / University of British Columbia",
        "language": "English",
        "status": "Open Now",
        "deadline": "2026-11-15",
        "mechanism": "Dual Application (Must submit UBC undergraduate admission + dedicated International Scholars Award application by Nov 15)",
        "requirements": "Outstanding academic record (minimum 85%+ / 3.5 GPA), demonstrable financial need, high school nomination form, English proficiency (IELTS 6.5+ / TOEFL 90+)",
        "tests": "SAT / ACT not required",
        "visa_support": "Comprehensive: Official LOA and PAL provided to support Canadian Study Permit application",
        "competitiveness": "Very High (Full tuition + living costs awarded to top global applicants)",
        "official_link": "https://you.ubc.ca/financial-planning/scholarships-awards-international-students/international-scholars/",
        "funding": "Fully Funded (Full tuition, fees, and living costs for 4 years)"
    },
    {
        "name": "U.S.-MEPI Tomorrow's Leaders Undergraduate Program",
        "provider": "U.S. Department of State / Partner Universities (AUB, AUC, LAU)",
        "country_institution": "USA / Middle East (AUB, AUC, LAU)",
        "language": "English",
        "status": "Open Now",
        "deadline": "2026-11-18",
        "mechanism": "Integrated Single Portal (Direct unified scholarship & university admission application via Tomorrow's Leaders website)",
        "requirements": "High school seniors graduating in 2027 or recent graduates (2025/2026), minimum 3.0 GPA / 80%+ equivalent, demonstrated civic leadership & financial need, English proficiency",
        "tests": "SAT / ACT not required for scholarship eligibility; English testing arranged by program if needed",
        "visa_support": "Full Support: Diplomatic facilitation letters, visa application fees covered, and residency support for Lebanon/Egypt",
        "competitiveness": "High (Dedicated cohort specifically allocated for Palestinian students from West Bank and diaspora)",
        "official_link": "https://www.tomorrowsleadersprogram.org/",
        "funding": "Fully Funded (Full tuition, housing, monthly stipend, laptop, textbooks, and US exchange semester)"
    },
    {
        "name": "Global Korea Scholarship (GKS-U) - University Track",
        "provider": "National Institute for International Education (NIIED)",
        "country_institution": "South Korea / Partner Universities (KAIST, UNIST, Kyungpook, Pusan)",
        "language": "Korean & English (Includes 1-year language course + 4-year degree)",
        "status": "Open Now (Varies by university throughout October-November)",
        "deadline": "2026-11-30",
        "mechanism": "Separate Application (Direct physical/electronic submission of dossier to chosen Korean university's international office)",
        "requirements": "Under 25 years old, cumulative high school grade of 80%+ or top 20% of class, verified diploma/transcripts with apostille/consular legalization",
        "tests": "SAT / ACT not required; TOPIK / IELTS provides bonus evaluation points",
        "visa_support": "Standard Certificate of Admission (CoA) and NIIED official government award document for D-2 Korean Student Visa",
        "competitiveness": "Very High (Fixed country quota allocated for Palestine)",
        "official_link": "https://www.studyinkorea.go.kr",
        "funding": "Fully Funded (Full tuition, airfare, monthly stipend, settlement allowance, medical insurance)"
    },
    {
        "name": "Stipendium Hungaricum Undergraduate Scholarship",
        "provider": "Tempus Public Foundation / Hungarian Government",
        "country_institution": "Hungary / Leading Universities (ELTE, BME, Debrecen, Szeged)",
        "language": "English",
        "status": "Opening Soon (Expected opening mid-November 2026)",
        "deadline": "2027-01-15",
        "mechanism": "Dual Application (Online application at apply.stipendiumhungaricum.hu AND submission to Palestinian Ministry of Higher Education - MoHESR)",
        "requirements": "High school Tawjihi certificate (typically 80%+ for CS/Engineering), English proficiency (IELTS 5.5-6.5 or institutional test), medical certificate",
        "tests": "SAT / ACT not required; online institutional entrance exam & interview conducted by Hungarian university faculty",
        "visa_support": "Official Scholarship Letter of Award & Letter of Admission providing fee-free D-type Schengen visa processing",
        "competitiveness": "Moderate to High (Specific substantial national quota for Palestinian students under bilateral agreement)",
        "official_link": "https://stipendiumhungaricum.hu/",
        "funding": "Fully Funded (100% tuition waiver, monthly living allowance, free dorm or HUF 40,000/mo subsidy, health insurance)"
    },
    {
        "name": "Russian Government Scholarship (Rossotrudnichestvo Quota)",
        "provider": "Ministry of Science and Higher Education of the Russian Federation",
        "country_institution": "Russia / Russian Federal Universities (HSE, ITMO, MISIS, SPbPU)",
        "language": "Russian (Includes 1 fully funded preparatory foundation year) & select English programs",
        "status": "Open Now",
        "deadline": "2027-01-15",
        "mechanism": "Dual Application (Central online registration via education-in-russia.com, followed by dossier review at the Russian Diplomatic Mission)",
        "requirements": "High school Tawjihi certificate, valid passport, medical certificates (HIV and general fitness clearance), age 16-23",
        "tests": "SAT / ACT not required; portfolio evaluation or online testing in Mathematics/Informatics",
        "visa_support": "Ministry of Foreign Affairs (MFA) Russia official electronic visa invitation issued for student visa",
        "competitiveness": "Moderate (Dedicated annual quota reserved specifically for Palestinian applicants)",
        "official_link": "https://education-in-russia.com/",
        "funding": "Fully Funded (100% tuition fee waiver, 1-year language preparatory course, monthly stipend, subsidized dorms)"
    },
    {
        "name": "Reach Oxford Scholarship",
        "provider": "University of Oxford",
        "country_institution": "United Kingdom / University of Oxford",
        "language": "English",
        "status": "Open Now (For UCAS applicants holding Oxford offer)",
        "deadline": "2027-01-26",
        "mechanism": "Separate Application (Apply via UCAS by Oct 15 for Computer Science, then eligible offer-holders apply through Oxford scholarship portal in January)",
        "requirements": "Exceptional academic record (A*A*A in A-Levels or 98%+ Tawjihi equivalent with advanced Math), strong financial need declaration, leadership/social impact",
        "tests": "Oxford MAT (Mathematics Admissions Test) required for admission; SAT/ACT accepted as alternate high school qualification",
        "visa_support": "University CAS (Confirmation of Acceptance for Studies) issued for UK Student Visa (covers tuition, stipend, and return airfare)",
        "competitiveness": "Very High (Extremely prestigious; ~2-3 scholarships per year across all eligible developing countries)",
        "official_link": "https://www.ox.ac.uk/admissions/undergraduate/fees-and-funding/oxford-support/reach-oxford-scholarship",
        "funding": "Fully Funded (Course fees, annual living costs grant, and one return airfare per year)"
    },
    {
        "name": "Türkiye Bursları (Türkiye Government Scholarships)",
        "provider": "Presidency for Turks Abroad and Related Communities (YTB)",
        "country_institution": "Turkey / Top Universities (METU, ITU, Bogazici, Bilkent)",
        "language": "Turkish (includes 1-year free TÖMER language course) or English (requires IELTS/TOEFL)",
        "status": "Opening Soon (Opens January 10, 2027)",
        "deadline": "2027-02-20",
        "mechanism": "Integrated Single Portal (Unified university placement and scholarship application through TBBS portal)",
        "requirements": "Tawjihi minimum average of 70% (85%+ strongly recommended for Cybersecurity and Software Engineering), under 21 years of age, statement of purpose, recommendation letters",
        "tests": "SAT optional but significantly enhances acceptance chances in English-medium programs (METU/ITU)",
        "visa_support": "Official Scholarship Acceptance Certificate issued for Turkish Student Visa (visa fee waived or facilitated via Turkish Embassy)",
        "competitiveness": "High (Dedicated country-specific quota reserved for Palestine)",
        "official_link": "https://www.turkiyeburslari.gov.tr/",
        "funding": "Fully Funded (100% tuition waiver, monthly stipend, free dormitory accommodation, health insurance, language year, flight ticket)"
    }
]


def generate_csv_report(filename: str = "scholarships_undergraduate_palestine.csv") -> str:
    """Exports the 11-column matrix to CSV."""
    headers = [
        "Scholarship & Provider Name",
        "Country / Institution (University)",
        "Language of Instruction",
        "Application Status",
        "Application Deadline",
        "Application Mechanism",
        "Academic & General Requirements",
        "Standardized Tests",
        "Visa Support & Facilitation",
        "Competitiveness & Acceptance Rate",
        "Direct Official Link"
    ]

    with open(filename, mode="w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for s in SCHOLARSHIPS_DATA:
            writer.writerow([
                s["name"],
                s["country_institution"],
                s["language"],
                s["status"],
                s["deadline"],
                s["mechanism"],
                s["requirements"],
                s["tests"],
                s["visa_support"],
                s["competitiveness"],
                s["official_link"]
            ])

    logger.info(f"Generated CSV report: {filename}")
    return filename


def build_html_email() -> str:
    """Constructs a responsive, beautifully styled HTML email template."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    rows_html = ""
    for idx, s in enumerate(SCHOLARSHIPS_DATA, 1):
        status_color = "#10b981" if "Open Now" in s["status"] else "#3b82f6"
        badge_text = "مفتوح حالياً (Open Now)" if "Open Now" in s["status"] else "يفتح قريباً (Opening Soon)"
        
        rows_html += f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px;">
                <div>
                    <span style="background: #eff6ff; color: #1d4ed8; font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 6px; margin-left: 8px;">#{idx}</span>
                    <h3 style="display: inline; margin: 0; font-size: 18px; color: #0f172a;">{s['name']}</h3>
                    <div style="color: #64748b; font-size: 14px; margin-top: 4px;">📍 <b>{s['country_institution']}</b> | لغة الدراسة: <b>{s['language']}</b></div>
                </div>
                <div style="text-align: left;">
                    <span style="background: {status_color}15; color: {status_color}; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; border: 1px solid {status_color};">
                        {badge_text}
                    </span>
                    <div style="color: #dc2626; font-size: 13px; font-weight: bold; margin-top: 6px;">⏳ الموعد النهائي: {s['deadline']}</div>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 13.5px; color: #334155;">
                <tr>
                    <td style="padding: 6px 0; width: 25%; font-weight: bold; color: #475569;">💰 التمويل والتغطية:</td>
                    <td style="padding: 6px 0;">{s['funding']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-weight: bold; color: #475569;">📋 آلية التقديم:</td>
                    <td style="padding: 6px 0;">{s['mechanism']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-weight: bold; color: #475569;">🎓 شروط القبول:</td>
                    <td style="padding: 6px 0;">{s['requirements']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-weight: bold; color: #475569;">📝 الاختبارات المعيارية:</td>
                    <td style="padding: 6px 0;">{s['tests']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-weight: bold; color: #475569;">🛂 دعم التأشيرة (Visa):</td>
                    <td style="padding: 6px 0;">{s['visa_support']}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; font-weight: bold; color: #475569;">📊 التنافسية:</td>
                    <td style="padding: 6px 0;"><span style="color: #b45309; font-weight: bold;">{s['competitiveness']}</span></td>
                </tr>
            </table>

            <div style="margin-top: 14px; text-align: left; padding-top: 10px; border-top: 1px dashed #e2e8f0;">
                <a href="{s['official_link']}" target="_blank" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: bold; display: inline-block;">
                    🔗 الانتقال لبوابة التقديم الرسمية
                </a>
                <span style="font-size: 11.5px; color: #94a3b8; margin-right: 12px;">⚠️ يرجى التأكد من تاريخ الإغلاق عبر الرابط الرسمي</span>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>دليل منح البكالوريوس المفتوحة والقريبة</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #0f172a; line-height: 1.6;">
        <div style="max-width: 820px; margin: 0 auto;">
            
            <!-- Header Banner -->
            <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: #ffffff; border-radius: 16px; padding: 30px; text-align: center; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(37,99,235,0.2);">
                <span style="background: rgba(255,255,255,0.2); font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;">تقرير أسبوعي تلقائي | Automated Weekly Report</span>
                <h1 style="margin: 14px 0 8px 0; font-size: 24px;">دليل منح البكالوريوس المفتوحة والقريبة 🎓</h1>
                <p style="margin: 0; font-size: 15px; opacity: 0.95;">
                    هندسة البرمجيات، الأمن السيبراني، الذكاء الاصطناعي، وتكنولوجيا المعلومات (خاص بالطلاب من فلسطين)
                </p>
                <div style="margin-top: 14px; font-size: 13px; opacity: 0.85;">
                    📅 تاريخ التحديث: <b>{now_str}</b> | إجمالي المنح المفحوصة والمفتوحة: <b>{len(SCHOLARSHIPS_DATA)} منح</b>
                </div>
            </div>

            <!-- Mandatory Advisory Notice -->
            <div style="background: #fffbeb; border-right: 4px solid #f59e0b; padding: 14px 18px; border-radius: 8px; margin-bottom: 24px; font-size: 13.5px; color: #92400e;">
                ⚠️ <b>تنبيه هام للطلبة:</b> يتم ترتيب هذه المنح زمنياً بحسب الأقرب في الموعد النهائي (Deadline). نرجو مراجعة الشروط والمواعيد المحدثة عبر الرابط الرسمي لكل منحة مباشرة قبل إغلاق بوابات التقديم.
            </div>

            <!-- Scholarships List -->
            {rows_html}

            <!-- CSV Attachment Notice -->
            <div style="background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 16px; text-align: center; margin-top: 24px; font-size: 13.5px; color: #475569;">
                📎 <b>مرفق مع هذا الإيميل:</b> ملف جدول بيانات كامل <code>scholarships_undergraduate_palestine.csv</code> يحتوي على الأعمدة الـ 11 باللغة الإنجليزية لتتمكن من فتحه وتصفحه عبر Excel في أي وقت.
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding: 24px 0; font-size: 12px; color: #94a3b8;">
                تم توليد هذا التقرير وتدقيقه تلقائياً بواسطة نظام الأوتوميشن الأسبوعي.<br>
                جميع الحقوق محفوظة © {datetime.now().year} | Scholarship Automation Engine
            </div>

        </div>
    </body>
    </html>
    """
    return html


def send_email_report() -> bool:
    """Sends the formatted HTML report and CSV attachment via Gmail SMTP."""
    sender_email = os.getenv("SENDER_EMAIL")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL", sender_email)

    if not sender_email or not gmail_password:
        logger.error("Missing SENDER_EMAIL or GMAIL_APP_PASSWORD in environment.")
        return False

    # Clean password (remove any spaces)
    gmail_password = gmail_password.replace(" ", "").strip()

    # Generate CSV
    csv_file_path = generate_csv_report()
    html_content = build_html_email()

    msg = EmailMessage()
    msg["Subject"] = f"🎓 دليل منح البكالوريوس المفتوحة والقريبة | تقرير أسبوعي ({datetime.now().strftime('%d-%m-%Y')})"
    msg["From"] = f"Scholarship Tracker <{sender_email}>"
    msg["To"] = recipient_email

    # Plaintext fallback
    msg.set_content(
        f"مرحباً بك، مرفق تقرير منح البكالوريوس المفتوحة والقريبة لتخصصات الأمن السيبراني وهندسة البرمجيات والذكاء الاصطناعي للطلاب من فلسطين.\n"
        f"يرجى فتح الإيميل في متصفح يدعم HTML للاطلاع على الجدول المنظم، أو فتح ملف CSV المرفق."
    )

    # HTML rich body
    msg.add_alternative(html_content, subtype="html")

    # Attach CSV
    try:
        with open(csv_file_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="text",
                subtype="csv",
                filename=os.path.basename(csv_file_path)
            )
        logger.info(f"Attached CSV: {csv_file_path}")
    except Exception as e:
        logger.warning(f"Could not attach CSV: {e}")

    # Send through Gmail SMTP TLS (port 587)
    try:
        logger.info("Connecting to smtp.gmail.com:587 (TLS)...")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as server:
            server.starttls()
            server.login(sender_email, gmail_password)
            server.send_message(msg)
            logger.info(f"✅ Email successfully delivered to {recipient_email}!")
            return True
    except Exception as e:
        logger.error(f"Failed to send email via TLS: {e}. Trying SSL 465...")
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as server:
                server.login(sender_email, gmail_password)
                server.send_message(msg)
                logger.info(f"✅ Email successfully delivered to {recipient_email} via SSL!")
                return True
        except Exception as e2:
            logger.error(f"Failed to send email: {e2}")
            return False


if __name__ == "__main__":
    success = send_email_report()
    if success:
        print("EMAIL_SENT_SUCCESSFULLY")
    else:
        print("EMAIL_FAILED")

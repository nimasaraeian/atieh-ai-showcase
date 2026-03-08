# ai_brain.py
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import cast, String, func
from sqlalchemy.orm import Session

from models import Patient, Appointment, PaymentType
from scoring_algorithm import AppointmentScoringAlgorithm


class AIBrain:
    """
    AIBrain در نسخه ۱:
    - روی منطق امتیازدهی فعلی سوار می‌شود
    - ساختار لازم برای اضافه‌کردن ML واقعی در آینده را فراهم می‌کند
    """

    def __init__(self):
        # اینجا بعدها می‌توانیم مدل‌های ML را load کنیم (مثلاً با joblib)
        self.models_loaded = False

    @staticmethod
    def _normalize_payment_type(raw) -> Optional[str]:
        """
        Safely convert a payment_type value to a normalized uppercase string.

        Handles three input shapes:
          - PaymentType enum instance  -> use .value then upper-case
          - plain string from DB       -> lower-strip, then map
          - None                       -> return None

        Normalization rules:
          'cash' / 'CASH'          -> 'CASH'
          'insurance*'             -> 'INSURANCE'   (generic; no number)
          'insurance_N' / 'INSURANCE_N' -> 'INSURANCE_N'  (keep specifics)
          anything else            -> 'UNKNOWN'
        """
        if raw is None:
            return None
        # Resolve enum to its .value string safely
        if hasattr(raw, "value"):
            raw = raw.value
        s = str(raw).strip().lower()
        if s == "cash":
            return "CASH"
        if s == "insurance":
            return "INSURANCE"
        if s.startswith("insurance_"):
            return s.upper()          # e.g. 'INSURANCE_1', 'INSURANCE_15'
        return "UNKNOWN"

    def extract_features(
        self,
        db: Session,
        patient: Patient,
        treatment_type: Optional[str] = None,  # اختیاری - می‌تواند خالی باشد
        appointment_date: Optional[datetime] = None,
        payment_type: Optional[PaymentType] = None,  # اختیاری - اگر مشخص نشود، از patient استفاده می‌شود
    ) -> Dict[str, Any]:
        """
        استخراج featureهای اولیه برای AI.
        الان ساده است، اما ساختار آن طوری طراحی شده که بعداً برای ML استفاده شود.
        """
        # Query only the three columns actually used in the loop.
        # Using with_entities() returns lightweight Row objects instead of full
        # ORM Appointment instances, which prevents SQLAlchemy from attempting
        # to map DB values like 'insurance' into the PaymentType enum and
        # raising LookupError.  cast(..., String) ensures the status column
        # is always returned as a plain string even if the DB dialect returns
        # it differently.
        rows = (
            db.query(
                cast(Appointment.status, String).label("status"),
                Appointment.did_patient_show_up,
                Appointment.paid_on_time,
            )
            .filter(Appointment.patient_id == patient.id)
            .filter(Appointment.status.in_(["completed", "cancelled"]))
            .all()
        )
        num_prev = len(rows)

        num_no_show = sum(1 for r in rows if r.did_patient_show_up is False)
        num_late_payments = sum(1 for r in rows if r.paid_on_time is False)

        # محاسبه تعداد نوبت‌های تکمیل شده
        num_completed = sum(1 for r in rows if r.status == "completed")

        # محاسبه نسبت تکمیل شده به کل
        completion_rate = num_completed / num_prev if num_prev > 0 else 0.0

        # تعیین نوع پرداخت: اول از پارامتر، سپس از patient
        # Use the safe normalizer to avoid crashes when patient.payment_type
        # holds an unexpected DB value.
        raw_payment = payment_type if payment_type is not None else patient.payment_type
        normalized_payment = self._normalize_payment_type(raw_payment)

        features = {
            "payment_type": normalized_payment,
            "treatment_type": treatment_type,
            "lifetime_months": self._estimate_lifetime_months(patient),
            "num_prev_appointments": num_prev,
            "num_completed": num_completed,
            "completion_rate": completion_rate,
            "num_no_show": num_no_show,
            "num_late_payments": num_late_payments,
            "day_of_week": appointment_date.weekday() if appointment_date else None,
            "hour": appointment_date.hour if appointment_date else None,
        }
        return features

    def _estimate_lifetime_months(self, patient: Patient) -> int:
        if not patient.first_visit_date:
            return 0
        now = datetime.now(timezone.utc)
        # تبدیل first_visit_date به timezone-aware اگر نیست
        if patient.first_visit_date.tzinfo is None:
            first_visit = patient.first_visit_date.replace(tzinfo=timezone.utc)
        else:
            first_visit = patient.first_visit_date
        delta = now - first_visit
        return max(0, int(delta.days / 30))

    def predict_risk_and_value(
        self, features: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        نسخه اولیه: به جای مدل ML، از قواعد ساده استفاده می‌کند.
        بعداً این تابع با خروجی مدل ML جایگزین می‌شود.
        """
        # payment_type is already normalized to uppercase by _normalize_payment_type()
        payment_type = (features["payment_type"] or "").upper()
        lifetime_months = features["lifetime_months"] or 0
        num_no_show = features["num_no_show"]
        num_late = features["num_late_payments"]

        # ریسک پایه
        risk_late = 0.2
        risk_no_show = 0.1

        # اثر نوع پرداخت
        if payment_type == "CASH":
            risk_late -= 0.1
        elif "INSURANCE_15" in payment_type or "INSURANCE_16" in payment_type or "INSURANCE_20" in payment_type:
            risk_late += 0.2

        # اثر سابقه
        if lifetime_months > 24:
            risk_late -= 0.05
            risk_no_show -= 0.05
        if num_no_show >= 2:
            risk_no_show += 0.2
        if num_late >= 2:
            risk_late += 0.2

        # clamp
        risk_late = float(max(0.0, min(1.0, risk_late)))
        risk_no_show = float(max(0.0, min(1.0, risk_no_show)))

        # محاسبه value_score بر اساس سابقه کامل بیمار
        base_value = 0.5
        
        # اثر نوع پرداخت
        if payment_type == "CASH":
            base_value += 0.25
        
        # اثر lifetime (سابقه عضویت)
        if lifetime_months > 24:
            base_value += 0.15
        elif lifetime_months > 12:
            base_value += 0.10
        elif lifetime_months > 6:
            base_value += 0.05
        
        # اثر تعداد نوبت‌های قبلی (بیماران با سابقه بیشتر ارزشمندترند)
        num_prev = features.get("num_prev_appointments", 0)
        if num_prev > 10:
            base_value += 0.10
        elif num_prev > 5:
            base_value += 0.05
        
        # اثر نرخ تکمیل (بیماران با نرخ تکمیل بالا ارزشمندترند)
        completion_rate = features.get("completion_rate", 0.0)
        if completion_rate > 0.9:
            base_value += 0.10
        elif completion_rate > 0.7:
            base_value += 0.05
        elif completion_rate < 0.5:
            base_value -= 0.10
        
        # اثر عدم حضور (بیماران با عدم حضور زیاد ارزش کمتری دارند)
        if num_no_show > 3:
            base_value -= 0.15
        elif num_no_show > 1:
            base_value -= 0.10
        elif num_no_show > 0:
            base_value -= 0.05
        
        # اثر پرداخت دیر (بیماران با پرداخت دیر ارزش کمتری دارند)
        if num_late > 3:
            base_value -= 0.15
        elif num_late > 1:
            base_value -= 0.10
        elif num_late > 0:
            base_value -= 0.05

        value_score = float(max(0.0, min(1.0, base_value)))
        
        # تبدیل value_score از 0-1 به 0-100 برای خروجی
        value_score_int = int(value_score * 100)

        return {
            "risk_late_payment": risk_late,
            "risk_no_show": risk_no_show,
            "value_score": value_score_int,  # حالا int است (0-100)
        }

    def compute_ai_priority(
        self,
        base_priority_score: float,
        risk_late_payment: float,
        risk_no_show: float,
        value_score: float,
    ) -> float:
        """
        ترکیب امتیاز فعلی + ارزش.
        ریسک‌ها از محاسبه حذف شده‌اند.
        """
        # وزن‌ها: base priority مهم‌تر است
        w_base = 0.7  # افزایش وزن base priority
        w_value = 0.3
        # w_risk حذف شده - ریسک‌ها در محاسبه استفاده نمی‌شوند

        # محاسبه امتیاز AI بدون در نظر گیری ریسک
        ai_score = (
            w_base * (base_priority_score / 100.0)
            + w_value * value_score
        )
        
        # اگر base_priority_score بالا باشد (>= 80)، امتیاز AI را تقویت می‌کنیم
        if base_priority_score >= 80:
            # برای امتیازهای بالا، حداقل 85% از base_priority را حفظ می‌کنیم
            min_score = base_priority_score * 0.85
            ai_score = max(ai_score, min_score / 100.0)
        
        # نرمال‌سازی به ۰-۱۰۰
        return float(max(0.0, min(100.0, ai_score * 100)))
    
    @staticmethod
    def _score_from_stats(
        lifetime_months: int,
        num_prev: int,
        num_completed: int,
        completion_rate: float,
        num_no_show: int,
        num_late: int,
    ) -> float:
        """
        Pure scoring formula — no DB access.

        Extracted from calculate_patient_history_score() so that batch
        endpoints (e.g. /ai/top-patients) can pre-compute the stats with a
        single aggregation query and call this method directly, avoiding the
        N+1 query pattern.
        """
        score = 50.0

        if lifetime_months > 24:
            score += 20
        elif lifetime_months > 12:
            score += 15
        elif lifetime_months > 6:
            score += 10
        elif lifetime_months > 3:
            score += 5

        if num_prev > 10:
            score += 15
        elif num_prev > 5:
            score += 10
        elif num_prev > 2:
            score += 5

        if completion_rate > 0.9:
            score += 10
        elif completion_rate > 0.7:
            score += 5
        elif completion_rate < 0.5:
            score -= 10

        if num_no_show > 3:
            score -= 15
        elif num_no_show > 1:
            score -= 10
        elif num_no_show > 0:
            score -= 5

        if num_late > 3:
            score -= 10
        elif num_late > 1:
            score -= 5
        elif num_late > 0:
            score -= 2

        return float(max(0.0, min(100.0, score)))

    def calculate_patient_history_score(
        self,
        db: Session,
        patient: Patient,
    ) -> float:
        """
        محاسبه امتیاز فقط بر اساس سابقه بیمار (بدون نوع درمان و نوع پرداخت)
        این امتیاز برای نمایش اولیه استفاده می‌شود
        """
        features = self.extract_features(
            db=db,
            patient=patient,
            treatment_type=None,
            appointment_date=None,
            payment_type=None,
        )
        return self._score_from_stats(
            lifetime_months=features.get("lifetime_months", 0),
            num_prev=features.get("num_prev_appointments", 0),
            num_completed=features.get("num_completed", 0),
            completion_rate=features.get("completion_rate", 0.0),
            num_no_show=features.get("num_no_show", 0),
            num_late=features.get("num_late_payments", 0),
        )


    @staticmethod
    def _classify(
        history_score: float,
        recency_days: Optional[int],
        cancelled_count: int,
        completed_count: int,
    ) -> tuple[str, str]:
        """
        Priority-ordered label rules (first match wins):

        1. VIP       — score >= 80
        2. STANDARD  — 50 <= score < 80
        3. RECALL    — recency_days > 180  (patient not seen in 6+ months)
        4. RISK      — cancellations outnumber completed visits
        5. RISK      — fallback for any remaining low-score patient
        """
        if history_score >= 80:
            return "VIP", "Priority booking — retain with early access to slots."
        if history_score >= 50:
            return "STANDARD", "Schedule a routine follow-up within 3 months."
        if recency_days is not None and recency_days > 180:
            return "RECALL", "Send a recall reminder — patient has not visited in over 6 months."
        if cancelled_count > completed_count:
            return "RISK", "Flag for review — cancellations outnumber completed visits."
        return "RISK", "Low engagement — consider outreach to re-engage this patient."

    def explain_patient(
        self,
        db: Session,
        patient: "Patient",
    ) -> Dict[str, Any]:
        """
        Manager explainability endpoint payload.

        Flat JSON with history score, appointment stats, decision label,
        and a short actionable recommendation. No Persian text.
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        one_year_ago = (now - timedelta(days=365)).replace(tzinfo=None)

        # ── appointment counts (single pass over a lightweight query) ──
        status_rows = (
            db.query(
                cast(Appointment.status, String).label("status"),
                func.count().label("cnt"),
            )
            .filter(Appointment.patient_id == patient.id)
            .group_by("status")
            .all()
        )
        counts: Dict[str, int] = {r.status: r.cnt for r in status_rows}
        visits_count: int = sum(counts.values())
        completed_count: int = counts.get("completed", 0)
        cancelled_count: int = counts.get("cancelled", 0)

        # ── last visit (MAX appointment_date across all statuses) ──
        last_visit_raw: Optional[datetime] = (
            db.query(func.max(Appointment.appointment_date))
            .filter(Appointment.patient_id == patient.id)
            .scalar()
        )
        last_visit_at: Optional[str] = (
            last_visit_raw.isoformat() if last_visit_raw else None
        )

        # ── recency ──
        recency_days: Optional[int] = None
        if last_visit_raw is not None:
            lv = last_visit_raw
            if lv.tzinfo is None:
                lv = lv.replace(tzinfo=timezone.utc)
            recency_days = (now - lv).days

        # ── predominant payment type (mode across all appointments) ──
        pt_row = (
            db.query(
                cast(Appointment.payment_type, String).label("pt"),
                func.count().label("cnt"),
            )
            .filter(
                Appointment.patient_id == patient.id,
                Appointment.payment_type.isnot(None),
            )
            .group_by("pt")
            .order_by(func.count().desc())
            .first()
        )
        predominant_payment_type: Optional[str] = (
            pt_row[0] if pt_row
            else self._normalize_payment_type(patient.payment_type)
        )

        # ── appointments in last 12 months ──
        total_appointments_last_12_months: int = (
            db.query(func.count())
            .filter(
                Appointment.patient_id == patient.id,
                Appointment.appointment_date >= one_year_ago,
            )
            .scalar()
            or 0
        )

        # ── history score (reuses existing formula) ──
        history_score = self.calculate_patient_history_score(db=db, patient=patient)

        # ── decision label + recommendation ──
        decision_label, recommendation = self._classify(
            history_score=history_score,
            recency_days=recency_days,
            cancelled_count=cancelled_count,
            completed_count=completed_count,
        )

        return {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "visits_count": visits_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "last_visit_at": last_visit_at,
            "recency_days": recency_days,
            "predominant_payment_type": predominant_payment_type,
            "total_appointments_last_12_months": total_appointments_last_12_months,
            "history_score": history_score,
            "decision_label": decision_label,
            "recommendation": recommendation,
        }


# یک نمونه global که در app.py استفاده می‌کنیم
ai_brain = AIBrain()




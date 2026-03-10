# -*- coding: utf-8 -*-
import sqlite3
import re

DB = r".\atieh_clinic.db"

WEEKDAYS = [
    "یکشنبه",
    "دوشنبه",
    "سه شنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
    "شنبه",
]

def extract_weekday(raw_text: str):
    if not raw_text:
        return None

    text = str(raw_text).replace("\u200c", " ").strip()

    # فقط ابتدای متن را بررسی می‌کنیم
    for day in WEEKDAYS:
        normalized_day = day.replace("\u200c", " ")
        if text.startswith(normalized_day):
            if normalized_day == "سه شنبه":
                return "سه شنبه"
            return normalized_day

    # fallback: اگر ابتدای متن خراب بود، از اولین occurrence استفاده کن
    for day in WEEKDAYS:
        normalized_day = day.replace("\u200c", " ")
        if normalized_day in text:
            if normalized_day == "سه شنبه":
                return "سه شنبه"
            return normalized_day

    return None

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # backup count
    total_slots = cur.execute("SELECT COUNT(*) FROM doctor_time_slots").fetchone()[0]
    total_shifts = cur.execute("SELECT COUNT(*) FROM doctor_shift_schedule").fetchone()[0]
    print(f"doctor_time_slots rows: {total_slots}")
    print(f"doctor_shift_schedule rows: {total_shifts}")

    # repair doctor_time_slots
    rows = cur.execute("SELECT slot_id, raw_text FROM doctor_time_slots").fetchall()
    updated_slots = 0
    for slot_id, raw_text in rows:
        weekday = extract_weekday(raw_text)
        if weekday:
            cur.execute(
                "UPDATE doctor_time_slots SET weekday_name = ? WHERE slot_id = ?",
                (weekday, slot_id)
            )
            updated_slots += 1

    # repair doctor_shift_schedule
    rows = cur.execute("SELECT shift_id, raw_text FROM doctor_shift_schedule").fetchall()
    updated_shifts = 0
    for shift_id, raw_text in rows:
        weekday = extract_weekday(raw_text)
        if weekday:
            cur.execute(
                "UPDATE doctor_shift_schedule SET weekday_name = ? WHERE shift_id = ?",
                (weekday, shift_id)
            )
            updated_shifts += 1

    # حذف slotهای نامعتبر
    cur.execute("DELETE FROM doctor_time_slots WHERE slot_start < '08:00' OR slot_start > '20:00'")
    deleted_bad_slots = cur.rowcount

    conn.commit()

    print(f"updated doctor_time_slots: {updated_slots}")
    print(f"updated doctor_shift_schedule: {updated_shifts}")
    print(f"deleted invalid time slots: {deleted_bad_slots}")

    print("\nDistribution after repair:")
    rows = cur.execute("""
        SELECT weekday_name, COUNT(*)
        FROM doctor_time_slots
        GROUP BY weekday_name
        ORDER BY weekday_name
    """).fetchall()

    for weekday_name, count in rows:
        print(f"{weekday_name}: {count}")

    print("\nSample Monday rows:")
    rows = cur.execute("""
        SELECT slot_id, doctor_id, weekday_name, slot_start, floor_label, COALESCE(unit_label, ''), raw_text
        FROM doctor_time_slots
        WHERE weekday_name = 'دوشنبه'
        ORDER BY slot_start
        LIMIT 20
    """).fetchall()

    for r in rows:
        print(r)

    conn.close()

if __name__ == "__main__":
    main()

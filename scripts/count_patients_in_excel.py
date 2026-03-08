"""
Count unique patients in Excel source files
"""
import sqlite3
import json
import sys
import io

# Fix Unicode output for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('atieh_clinic.db')
c = conn.cursor()

print('=' * 70)
print('Analysis of patients in Excel files')
print('=' * 70)

# Total rows in staging
c.execute('SELECT COUNT(*) FROM stg_appointments')
total_staging = c.fetchone()[0]
print(f'\n1. کل سطرهای اکسل: {total_staging:,}')

# Unique patient names in staging (from row_json)
print('\n2. Extracting patient names from Excel...')
c.execute('SELECT row_json FROM stg_appointments WHERE row_json IS NOT NULL')

unique_names = set()
unique_phones = set()
rows_with_name = 0
rows_with_phone = 0
processed = 0

for row in c.fetchall():
    processed += 1
    if processed % 50000 == 0:
        print(f'   Processed: {processed:,}')
    
    try:
        data = json.loads(row[0])
        
        # Try different name keys
        name = (data.get("'نام بيمار'") or 
                data.get("'نام'") or 
                data.get("'بیمار'") or 
                data.get("'نام و نام خانوادگی'") or '')
        
        # Try different phone keys  
        phone = (data.get("'تلفن'") or 
                 data.get("'موبایل'") or 
                 data.get("'موبايل'") or '')
        
        if name and str(name).strip() and str(name).strip() != 'nan':
            unique_names.add(str(name).strip())
            rows_with_name += 1
            
        if phone and str(phone).strip() and str(phone).strip() != 'nan':
            unique_phones.add(str(phone).strip())
            rows_with_phone += 1
    except:
        pass

print(f'\n   - Rows with name: {rows_with_name:,}')
print(f'   - Unique names: {len(unique_names):,}')
print(f'\n   - Rows with phone: {rows_with_phone:,}')
print(f'   - Unique phones: {len(unique_phones):,}')

# Patients in database
print('\n3. Patients saved in database:')
c.execute('SELECT COUNT(*) FROM patients')
total_patients = c.fetchone()[0]
print(f'   - Total patients: {total_patients:,}')

c.execute("SELECT COUNT(*) FROM patients WHERE name != 'نامشخص' AND name IS NOT NULL")
named_patients = c.fetchone()[0]
print(f'   - Patients with valid name: {named_patients:,}')

c.execute("SELECT COUNT(*) FROM patients WHERE name = 'نامشخص' OR name IS NULL")
unnamed_patients = c.fetchone()[0]
print(f'   - Unknown patients: {unnamed_patients:,}')

# Sample names
print('\n4. Sample names (first 10):')
c.execute("SELECT DISTINCT name FROM patients WHERE name != 'نامشخص' LIMIT 10")
for i, row in enumerate(c.fetchall(), 1):
    name_safe = row[0].encode('ascii', 'ignore').decode('ascii') if row[0] else ''
    print(f'   {i}. {name_safe if name_safe else "[Persian name]"}')

print('\n' + '=' * 70)
print('SUMMARY:')
print(f'  - Unique patients in Excel (by name): {len(unique_names):,}')
print(f'  - Unique patients in Excel (by phone): {len(unique_phones):,}')
print(f'  - Patients saved in system: {total_patients:,}')
print('=' * 70)

conn.close()

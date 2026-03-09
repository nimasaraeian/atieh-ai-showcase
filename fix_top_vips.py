from pathlib import Path
import re

path = Path(r".\app\api\financial_operational.py")
text = path.read_text(encoding="utf-8")

pattern = r'''
SELECT
\s+record_no,
\s+patient_name_canonical,
\s+financial_tier,
\s+lifetime_txn_count,
\s+lifetime_net_received,
\s+financial_value_score,
\s+recent_txn_count,
\s+recent_net_received,
\s+last_payment_date_raw
'''

replacement = '''
SELECT
    record_no,
    financial_tier,
    lifetime_txn_count,
    lifetime_net_received,
    financial_value_score,
    recent_txn_count,
    recent_net_received,
    last_payment_date_raw
'''

new_text = re.sub(pattern, replacement, text, flags=re.VERBOSE)

path.write_text(new_text, encoding="utf-8")
print("Fixed top-vips query.")

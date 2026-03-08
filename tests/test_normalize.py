from app.utils.doctor_name import normalize_doctor_name as n

print(n("دکتر احمدی"))
print(n("دکتر احمدی'"))
print(n("دکتر غیرموجود"))
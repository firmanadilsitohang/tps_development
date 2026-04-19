import re
import os

tpsg_file = r'c:\xampp\htdocs\project_tps\app\templates\tpsg\employees.html'
omdd_file = r'c:\xampp\htdocs\project_tps\app\templates\omdd\participants.html'

with open(tpsg_file, 'r', encoding='utf-8') as f:
    tpsg_content = f.read()

# Replace extends
content = tpsg_content.replace('{% extends "base.html" %}', '{% extends "omdd/base.html" %}')
content = content.replace('Master Directory Partisipan | TPS-G', 'Partisipan | OMDD System')
content = content.replace('tpsg.detail_employee', 'omdd.detail_employee')

# Remove form wrapper and delete button
content = re.sub(r'<form action="\{\{ url_for\(\'tpsg\.bulk_delete_employees\'\) \}\}" method="POST" id="bulkDeleteForm">', '', content)
content = re.sub(r'</form>', '', content)

delete_btn_regex = r'<button type="submit" class="btn btn-delete-mass.*?</button>'
content = re.sub(delete_btn_regex, '', content, flags=re.DOTALL)

info_circle_regex = r'<span class="text-secondary mb-4 small d-none d-sm-inline">.*?</span>'
content = re.sub(info_circle_regex, '', content, flags=re.DOTALL)

# Default to OMDD header
content = content.replace('DATABASE PARTISIPAN', 'DAFTAR PARTISIPAN')
content = content.replace('Manajemen Profil, Level, dan Monitoring Risiko Pensiun Manpower', 'OMDD — OPERATIONAL MANAGEMENT & DEVELOPMENT DIVISION')

with open(omdd_file, 'w', encoding='utf-8') as f:
    f.write(content)

import re

dash_file = r'c:\xampp\htdocs\project_tps\app\templates\omdd\dashboard.html'
detail_file = r'c:\xampp\htdocs\project_tps\app\templates\omdd\detail.html'

with open(dash_file, 'r', encoding='utf-8') as f:
    dash_content = f.read()

with open(detail_file, 'r', encoding='utf-8') as f:
    detail_content = f.read()

# 1. Remove workshop panel from dashboard
workshop_regex = r'<!-- ========== WORKSHOP EVALUATION PANEL ========== -->.*?</div><!-- /container -->'
dash_content = re.sub(workshop_regex, '</div><!-- /container -->', dash_content, flags=re.DOTALL)

# 2. Extract Spider Modal HTML
spider_modal_regex = r'(<!-- ====================================================\n     MODAL: SPIDER CHART EVALUASI WORKSHOP\n==================================================== -->.*?</div>\s*</div>\s*</div>)'
spider_match = re.search(spider_modal_regex, dash_content, flags=re.DOTALL)
spider_html = spider_match.group(1) if spider_match else ''

# 3. Remove Spider Modal from dashboard
if spider_html:
    dash_content = dash_content.replace(spider_html, '')

# 4. Remove Spider CSS from dashboard
css_regex = r'/\* ========================= MODAL EVALUASI \(SPIDER\) ========================= \*/.*?(?=/\* Activity Timeline \*/|</style>|/\* ============)'
css_match = re.search(css_regex, dash_content, flags=re.DOTALL)
spider_css = css_match.group(0) if css_match else ''
if spider_css:
    dash_content = dash_content.replace(spider_css, '')

# 5. Remove Spider Chart LOGIC from Dashboard
logic_regex = r'// --- SPIDER CHART LOGIC ---.*?(?=\n\s*</script>|// --- END)'
logic_match = re.search(logic_regex, dash_content, flags=re.DOTALL)
spider_js = logic_match.group(0) if logic_match else ''
if spider_js:
    # Also remove until end of script if no END marker
    dash_content = dash_content.replace(spider_js, '')
    # clean up any trailing empty script blocks safely
    
# Save Dashboard
with open(dash_file, 'w', encoding='utf-8') as f:
    f.write(dash_content)

# Now inject to detail.html

# Fix spider modal CSS
if '/* ========================= MODAL EVALUASI (SPIDER) ========================= */' not in detail_content and spider_css:
    detail_content = detail_content.replace('</style>', spider_css + '\n</style>')

# Ensure chart.js is imported
if 'chart.js' not in detail_content.lower():
    chart_js_script = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n'
    if '<script>' in detail_content:
        detail_content = detail_content.replace('<script>', chart_js_script + '<script>', 1)
    else:
        detail_content += '\n' + chart_js_script

# Add eval button to header
btn_html = """
            <button class="btn-eval-page" onclick="openSpiderModal()">
                <i class="fas fa-chart-radar"></i> Evaluasi Partisipan
            </button>
"""
if 'btn-eval-page' not in detail_content:
    detail_content = detail_content.replace('<div class="d-flex gap-2">', f'<div class="d-flex gap-2">{btn_html}')


# We need to adapt the Javascript for detail.html since we don't pass arguments to openSpiderModal()
# Instead, we just read from the Jinja variables directly
custom_js = """
    // --- SPIDER CHART LOGIC ---
    let spiderConfig = null;
    let spiderChartObj = null;

    function initSpiderChart(dataArray) {
        const ctx = document.getElementById('spiderChart').getContext('2d');
        spiderConfig = {
            type: 'radar',
            data: {
                labels: ['Genba', 'Analysis', 'Problem Solving', 'Kaizen', 'Observation'],
                datasets: [{
                    label: 'Skor Kompetensi',
                    data: dataArray,
                    backgroundColor: 'rgba(255, 0, 160, 0.2)',
                    borderColor: '#ff00a0',
                    pointBackgroundColor: '#00d2ff',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#39ff14',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.1)' },
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        pointLabels: { color: '#8b949e', font: { size: 10, family: 'Inter', weight: 'bold' } },
                        ticks: { display: false, min: 0, max: 100, stepSize: 20 }
                    }
                },
                plugins: { legend: { display: false } }
            }
        };
        if(spiderChartObj) spiderChartObj.destroy();
        spiderChartObj = new Chart(ctx, spiderConfig);
    }

    function syncInput(field) {
        const val = document.getElementById('input_' + field).value;
        document.getElementById('display_' + field).innerText = val;
        
        if (spiderChartObj) {
            const arr = [
                document.getElementById('input_genba').value,
                document.getElementById('input_analysis').value,
                document.getElementById('input_problem_solving').value,
                document.getElementById('input_kaizen').value,
                document.getElementById('input_observation').value
            ];
            spiderChartObj.data.datasets[0].data = arr;
            spiderChartObj.update();
        }
    }

    function openSpiderModal() {
        document.getElementById('spiderModal').classList.add('show');
        
        // Form action
        const empId = '{{ employee.id }}';
        document.getElementById('spiderForm').action = "/omdd/evaluate-workshop/" + empId;

        // Photo, etc.
        const photoUrl = '{{ employee.photo or "" }}';
        const name = '{{ employee.name }}';
        const empNameObj = encodeURIComponent(name);
        document.getElementById('spiderEmpPhoto').src = photoUrl ? photoUrl : "https://ui-avatars.com/api/?name=" + empNameObj + "&background=0d1117&color=c9d1d9&size=120";
        document.getElementById('spiderEmpName').innerText = name;
        document.getElementById('spiderEmpNik').innerText = '{{ employee.username }}';
        document.getElementById('spiderEmpPos').innerText = '{{ employee.position or "-" }}';

        // Set inputs
        const initialScores = [
            {{ ev.genba if ev else 0 }},
            {{ ev.analysis if ev else 0 }},
            {{ ev.problem_solving if ev else 0 }},
            {{ ev.kaizen if ev else 0 }},
            {{ ev.observation if ev else 0 }}
        ];

        document.getElementById('input_genba').value = initialScores[0];
        document.getElementById('input_analysis').value = initialScores[1];
        document.getElementById('input_problem_solving').value = initialScores[2];
        document.getElementById('input_kaizen').value = initialScores[3];
        document.getElementById('input_observation').value = initialScores[4];

        ['genba','analysis','problem_solving','kaizen','observation'].forEach(field => syncInput(field));
        
        document.getElementById('spiderNotes').value = `{{ ev.notes if ev and ev.notes else "" }}`;
        initSpiderChart(initialScores);
    }

    function closeSpiderModal() {
        document.getElementById('spiderModal').classList.remove('show');
    }
"""

if 'id="spiderModal"' not in detail_content and spider_html:
    detail_content = detail_content.replace('{% endblock %}', spider_html + '\n{% endblock %}')

if 'function openSpiderModal' not in detail_content:
    detail_content = detail_content.replace('<script>', '<script>\n' + custom_js)

with open(detail_file, 'w', encoding='utf-8') as f:
    f.write(detail_content)

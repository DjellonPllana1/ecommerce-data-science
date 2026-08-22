from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[2]/'dashboard/app.py'
PAGES=['Executive Overview','Sales Analytics','Customer Intelligence','Delivery Risk','Sales Forecasting','Model Performance','About the Project']

def test_every_dashboard_page_renders():
    app=AppTest.from_file(str(APP),default_timeout=45).run()
    assert not app.exception
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run(timeout=45)
        assert not app.exception, page
        assert any(page in heading.value for heading in app.header), page

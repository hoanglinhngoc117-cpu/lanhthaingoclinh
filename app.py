import sys
import json
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.models import CustomerRequest, OpportunityStatus
from src.agent_controller import MinhAnB2BAgent
from src.config import (
    SAMPLE_REQUESTS_PATH, SUMMARY_DASHBOARD_PATH, AUDIT_LOG_PATH,
    DOSSIERS_DIR, DRAFT_EMAILS_DIR, APPROVAL_TICKETS_DIR, REPO_OUTPUT_DIR
)

app = FastAPI(title="Minh An Technology - AI Agent B2B Sales API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Agent
agent = MinhAnB2BAgent()

class ProcessRequestInput(BaseModel):
    customer_name: str
    tier: Optional[str] = "STANDARD"
    contact_person: Optional[str] = ""
    contact_email: Optional[str] = ""
    contact_phone: Optional[str] = ""
    raw_request_text: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    for rel_path in ["index.html", "public/index.html", "web/index.html"]:
        p = BASE_DIR / rel_path
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "<h1>Minh An AI Agent Server Running</h1>"

@app.get("/api/data")
def get_data():
    # Đọc Dashboard
    dashboard = {}
    if SUMMARY_DASHBOARD_PATH.exists():
        dashboard = json.loads(SUMMARY_DASHBOARD_PATH.read_text(encoding="utf-8"))

    # Đọc Sample Requests và lấy thông tin trạng thái từ dossiers
    requests_list = []
    if SAMPLE_REQUESTS_PATH.exists():
        samples = json.loads(SAMPLE_REQUESTS_PATH.read_text(encoding="utf-8"))
        for s in samples:
            opp_id = s["id"].replace("REQ-", "OPP-")
            dossier_file = DOSSIERS_DIR / f"Dossier_{opp_id}.md"
            status = "PENDING_APPROVAL"
            net_total = 0.0
            approval_level = "SALES_REP"

            if dossier_file.exists():
                text = dossier_file.read_text(encoding="utf-8")
                import re
                m_st = re.search(r"\*\*Trạng thái\*\*:\s*`?([A-Z_]+)`?", text)
                if m_st:
                    status = m_st.group(1)
                m_lv = re.search(r"\*\*Cấp thẩm quyền\*\*:\s*`?([A-Z_]+)`?", text)
                if m_lv:
                    approval_level = m_lv.group(1)
                m_val = re.search(r"Tổng giá trị thanh toán \(Net\)\*\*:\s*`?([\d\.,]+)", text)
                if m_val:
                    clean_val = m_val.group(1).replace(".", "").replace(",", "")
                    try:
                        net_total = float(clean_val)
                    except ValueError:
                        pass

            requests_list.append({
                "id": s["id"],
                "customer_name": s["customer_name"],
                "contact_person": s.get("contact_person", "Chưa rõ"),
                "status": status,
                "net_total": net_total,
                "approval_level": approval_level
            })

    return {
        "dashboard": dashboard,
        "requests": requests_list
    }

@app.get("/api/audit", response_class=PlainTextResponse)
def get_audit_log():
    for p in [AUDIT_LOG_PATH, REPO_OUTPUT_DIR / "logs" / "execution_audit.log"]:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "Chưa có log kiểm toán."

@app.get("/api/doc", response_class=PlainTextResponse)
def get_doc(type: str = Query(...), id: str = Query(...)):
    clean_id = id.replace("OPP-", "")
    candidates = []
    if type == "dossier":
        candidates = [
            DOSSIERS_DIR / f"Dossier_{id}.md",
            REPO_OUTPUT_DIR / "dossiers" / f"Dossier_{id}.md",
            DOSSIERS_DIR / f"Dossier_OPP-{clean_id}.md",
            REPO_OUTPUT_DIR / "dossiers" / f"Dossier_OPP-{clean_id}.md"
        ]
    elif type == "email":
        candidates = [
            DRAFT_EMAILS_DIR / f"Email_{id}.txt",
            REPO_OUTPUT_DIR / "draft_emails" / f"Email_{id}.txt",
            DRAFT_EMAILS_DIR / f"Email_OPP-{clean_id}.txt",
            REPO_OUTPUT_DIR / "draft_emails" / f"Email_OPP-{clean_id}.txt"
        ]
    elif type == "ticket":
        candidates = [
            APPROVAL_TICKETS_DIR / f"Ticket_TICKET-{id}.md",
            REPO_OUTPUT_DIR / "approval_tickets" / f"Ticket_TICKET-{id}.md",
            APPROVAL_TICKETS_DIR / f"Ticket_TICKET-OPP-{clean_id}.md",
            REPO_OUTPUT_DIR / "approval_tickets" / f"Ticket_TICKET-OPP-{clean_id}.md"
        ]

    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

@app.post("/api/process")
def process_single(input_data: ProcessRequestInput):
    from datetime import datetime
    req_id = f"REQ-LIVE-{datetime.now().strftime('%M%S')}"
    
    req = CustomerRequest(
        id=req_id,
        customer_name=input_data.customer_name,
        contact_person=input_data.contact_person,
        contact_email=input_data.contact_email,
        contact_phone=input_data.contact_phone,
        tier=input_data.tier or "STANDARD",
        raw_request_text=input_data.raw_request_text
    )

    result = agent.process_request(req)
    d = result["dossier"]

    return {
        "opp_id": d.opportunity_id,
        "status": d.status.value,
        "net_total": d.net_total_vnd,
        "discount_pct": d.discount_pct,
        "approval_level": d.approval_level.value,
        "lead_time_days": d.feasible_lead_time_days,
        "basis": d.basis_of_decision,
        "escalation_reasons": d.escalation_reasons,
        "missing_fields": d.missing_fields
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()
    
    port = args.port
    print("=" * 80)
    print("   MINH AN TECHNOLOGY - AI AGENT FASTAPI LOCALHOST SERVER")
    print(f"   Giao dien Web: http://localhost:{port}")
    print(f"   Tai lieu API:  http://localhost:{port}/docs")
    print("=" * 80)
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)


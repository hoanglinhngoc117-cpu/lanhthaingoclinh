import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.models import CustomerRequest
from src.agent_controller import MinhAnB2BAgent
from src.config import SAMPLE_REQUESTS_PATH, OUTPUT_DIR

def run_tests(data_file_path: str = None):
    input_path = Path(data_file_path) if data_file_path else SAMPLE_REQUESTS_PATH
    print("=" * 80)
    print("   HỆ THỐNG AI AGENT XỬ LÝ CƠ HỘI BÁN HÀNG B2B - CÔNG TY MINH AN")
    print(f"   Đang nạp dữ liệu từ: {input_path}")
    print("=" * 80)

    if not input_path.exists():
        print(f"[LỖI] Không tìm thấy file dữ liệu: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    requests_list = []
    for item in raw_items:
        requests_list.append(CustomerRequest(
            id=item["id"],
            customer_name=item["customer_name"],
            contact_person=item.get("contact_person"),
            contact_email=item.get("contact_email"),
            contact_phone=item.get("contact_phone"),
            tier=item.get("tier", "STANDARD"),
            raw_request_text=item["raw_request_text"],
            test_category=item.get("test_category"),
            description=item.get("description")
        ))

    agent = MinhAnB2BAgent()
    batch_output = agent.process_batch(requests_list)
    results = batch_output["results"]
    dashboard = batch_output["dashboard"]

    print("\n" + "=" * 80)
    print("                 KẾT QUẢ XỬ LÝ TỪNG CƠ HỘI KINH DOANH")
    print("=" * 80)
    print(f"{'MÃ OPP':<14} | {'KHÁCH HÀNG':<26} | {'TRẠNG THÁI':<18} | {'GIÁ TRỊ (VNĐ)':<15} | {'CẤP DUYỆT':<14}")
    print("-" * 95)

    for r in results:
        d = r["dossier"]
        val_str = f"{d.net_total_vnd:,.0f}" if d.net_total_vnd > 0 else "0"
        print(f"{d.opportunity_id:<14} | {d.customer_name[:24]:<26} | {d.status.value:<18} | {val_str:>15} | {d.approval_level.value:<14}")

    print("\n" + "=" * 80)
    print("           BẢNG TỔNG HỢP THEO QUY CHUẨN BAN GIÁM ĐỐC MINH AN")
    print("=" * 80)
    sc = dashboard["summary_counts"]
    print(f"  * Tổng số yêu cầu đã xử lý:             {dashboard['total_requests_processed']}")
    print(f"  * [1] Số cơ hội CÓ THỂ TIẾP TỤC:        {sc['can_proceed']}")
    print(f"  * [2] Số cơ hội CẦN BỔ SUNG THÔNG TIN:  {sc['needs_info']}")
    print(f"  * [3] Số cơ hội CHƯA ĐÁP ỨNG:           {sc['cannot_fulfill']}")
    print(f"  * [4] Số cơ hội CHỜ DUYỆT (vượt quyền): {sc['pending_approval']}")
    print("-" * 80)
    print(f"  >>> TỔNG GIÁ TRỊ CÁC CƠ HỘI ĐỦ ĐIỀU KIỆN TIẾP TỤC HOẶC CHỜ DUYỆT:")
    print(f"      {dashboard['financial_summary']['total_qualified_or_pending_value_formatted']}")
    print("=" * 80)
    print(f"\n[OK] Toàn bộ hồ sơ đã xuất tại: {OUTPUT_DIR}")
    print(f"[OK] Nhật ký truy vết Audit Trail tại: {OUTPUT_DIR / 'logs' / 'execution_audit.log'}\n")

if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_tests(file_arg)


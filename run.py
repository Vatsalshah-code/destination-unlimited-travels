import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    if curr_dir not in sys.path:
        sys.path.insert(0, curr_dir)

    print("=================================================================")
    print("   DESTINATION UNLIMITED TRAVELS - DOCUMENT PORTAL              ")
    print("=================================================================")
    print("   Client Link (This Machine): http://127.0.0.1:8000/upload-documents")
    print("   Client Link (Mobile/Wi-Fi): http://192.168.1.9:8000/upload-documents")
    print("   Client Status Tracking    : http://192.168.1.9:8000/track")
    print("   Staff Admin Dashboard     : http://127.0.0.1:8000/admin/dashboard")
    print("   Staff Login               : admin@chintan.com / Chintan@123")
    print("=================================================================\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

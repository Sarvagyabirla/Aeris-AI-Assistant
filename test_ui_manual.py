import sys
import threading
import time

from PySide6.QtWidgets import QApplication

from aeris.assistant import AerisAssistant
from aeris.ui.desktop import AerisMainWindow


def verify_stop_button():
    app = QApplication(sys.argv)
    assistant = AerisAssistant()
    
    # Let's register a slow dummy tool
    def slow_tool(args, token=None):
        for i in range(10):
            if token:
                token.raise_if_cancelled()
            time.sleep(0.5)
        return {"success": True, "message": "Finished"}
        
    # We patch the router to return a slow action instead of using Gemini
    original_route = assistant.router.route
    def mock_route(text):
        from aeris.models import ActionRequest, PlannedResponse
        if text == "sleep test":
            return PlannedResponse(reply="Sleeping", actions=[ActionRequest(tool="system.status", arguments={})])
        return original_route(text)
        
    assistant.router.route = mock_route
    
    class DummyToken:
        def raise_if_cancelled(self):
            pass
            
    # Mock execute to just sleep and check token
    def mock_execute(action, approval, token=None):
        for i in range(10):
            if token:
                token.raise_if_cancelled()
            time.sleep(0.2)
        from aeris.models import ActionResult
        return ActionResult(True, "Finished")
    assistant.registry.execute = mock_execute

    window = AerisMainWindow(assistant)
    window.show()

    def simulate_user():
        time.sleep(1)
        # Type and send
        window.dashboard.input_field.setText("sleep test")
        window.dashboard.send_btn.click()
        
        time.sleep(0.5)
        # Should be "Thinking..."
        assert window.dashboard.status_label.text() == "Thinking..."
        
        # Click Stop
        window.dashboard.stop_btn.click()
        
        time.sleep(0.5)
        # Should be "Ready"
        assert window.dashboard.status_label.text() == "Ready"
        
        print("UI Integration verified!")
        window.close()
        app.quit()
        
    t = threading.Thread(target=simulate_user)
    t.start()
    
    app.exec()
    print("Test finished.")

if __name__ == "__main__":
    verify_stop_button()

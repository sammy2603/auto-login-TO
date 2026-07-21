class GameClient:

    def __init__(
        self,
        window_service,
        vision_service,
        input_service,
    ):
        self.window = window_service
        self.vision = vision_service
        self.input = input_service

    def connect(self):
        self.window.connect(
            title_substring=self.settings.window_title,
            timeout=self.settings.window_timeout,
    )   
    
    @property
    def hwnd(self):
        return self.window.hwnd
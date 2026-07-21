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
    
    def wait_template(
        self,
        template,
        timeout=30,
        threshold=0.9,
    ):
        return self.vision.wait_template(
            hwnd=self.hwnd,
            template=template,
            timeout=timeout,
            threshold=threshold,
    )

    def capture(self):
        return self.window.capture()
    
    def client_size(self):
        return self.window.client_size()
    
    @property
    def hwnd(self):
        return self.window.hwnd
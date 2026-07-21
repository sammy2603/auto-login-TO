from src.app.application import Application

app = Application()

try:
    app.start()
finally:
    app.shutdown()
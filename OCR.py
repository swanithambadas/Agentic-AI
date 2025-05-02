import io
from google.cloud import vision
from google.oauth2 import service_account

def ocr_event_image(image_path: str) -> str:
    # Point directly at your JSON key
    creds = service_account.Credentials.from_service_account_file(
        r"C:\Users\swani\Desktop\AI agent\ai-agent-vision-a689d5283676.json"
    )
    client = vision.ImageAnnotatorClient(credentials=creds)

    with io.open(image_path, 'rb') as img_file:
        content = img_file.read()
    image = vision.Image(content=content)

    response = client.text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"OCR error: {response.error.message}")

    return response.text_annotations[0].description if response.text_annotations else ""

if __name__ == "__main__":
    print("OCR’d text:\n", ocr_event_image("event.jpg"))

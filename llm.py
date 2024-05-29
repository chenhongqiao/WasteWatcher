import base64
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload
import io
from googleapiclient.errors import HttpError
import gspread
import socket
from datetime import datetime
import traceback
import re

with open("auth/openai_key.txt", "r") as file:
    api_key = file.read()

client = OpenAI(api_key=api_key)


scope = ["https://www.googleapis.com/auth/drive"]
service_account_json_key = "auth/google_key.json"
credentials = service_account.Credentials.from_service_account_file(
    filename=service_account_json_key, scopes=scope
)
drive_service = build("drive", "v3", credentials=credentials)

sheet_service = gspread.service_account(service_account_json_key)
sheet = sheet_service.open_by_key("1JvYjS1Ox1QxH4Njc5nVBXWKJfaDVVPz075MjCf0cuec")


hostname = socket.gethostname()


def detect_waste(ids):
    try:
        food_classes = [
            "juice_box",
            "fruit",
            "packaged_food",
            "resin",
            "milk",
            "yogurt",
            "none_of_the_above",
        ]
        prompts = {
            "juice_box": "Does the box look unopened? Pay attention to the short edge and see if there's a white straw sticking out. Note that if is the straw still intact in the wrap that is attached to the side of the juice box, that constitutes food waste. If the straw is detached or has been inserted in, that's not food waste. Remember that the images show an object falling down. Use your reasoning and give the best answer.",
            "fruit": "Are there visual evidence of edible parts left over?",
            "packaged_food": "Are there any food left in the wrap? Also pay attention to if the package has been opened. If there's food left of if the package is unopened, that's food waste and you should output <YES>.",
            "resin": "Does the box look unopened?",
            "milk": "Does the milk box look unopened? Can you clearly see the part that's teared open? If you can see it, reply <NO>, otherwise <YES>.",
            "yogurt": "Are there any remnant in the cup?",
            "none_of_the_above": "Do you think there's food waste?",
        }

        imgs = []
        for id in ids:
            # print(type(img))
            with open(f"log/{id}.jpg", "rb") as f:
                img_encoded = base64.b64encode(f.read()).decode("utf-8")
            imgs.append((id, img_encoded))

        imgs = sorted(imgs)

        system_content = [
            {
                "type": "text",
                "text": "You are an expert at detecting instances of food waste from images. You will be provided several images of an object, taken as it falls into the trash can. You will be asked a few questions about the images and the object by the user. When the user asks you to follow a specific format, always follow that format.",
            },
        ]

        img_content = [
            {
                "type": "text",
                "text": "Here are the photos. Analyze what's going on in each photo and then answer this question: Is there a identifiable food or beverage in the photos? Output your reasoning first and then end your response with <YES> or <NO>.",
            },
        ]
        # print(imgs)
        for img in imgs:
            img_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img[1]}",
                    },
                }
            )

        messages = [
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": img_content,
            },
        ]

        # print(messages)

        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            messages=messages,
            max_tokens=300,
        )

        print(response.choices[0].message.content)

        if "<NO>" in response.choices[0].message.content:
            return "NO"

        messages.append(response.choices[0].message)
        messages.append(
            {
                "role": "user",
                "content": f"What type of food is this? Select from this list: {json.dumps(food_classes)}. To help you distinguish juice box and milk, milk cartoons have the color of green and brown, while juice boxes are red, orange, or purple. Output your reasoning first and then end your response with the class in brackets. Example: <juice_box>.",
            },
        )

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            temperature=0.1,
            messages=messages,
            max_tokens=300,
        )

        print(response.choices[0].message.content)

        food_class = re.findall(r"\<.*?\>", response.choices[0].message.content)[0]
        food_class = food_class[1:-1]

        print(food_class)

        classification_prompt = prompts[food_class]

        messages.append(response.choices[0].message)
        messages.append(
            {
                "role": "user",
                "content": f"{classification_prompt} Output your reasoning first and then end your response with <YES> or <NO>.",
            },
        )

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            temperature=0.1,
            messages=messages,
            max_tokens=300,
        )

        print(response.choices[0].message.content)
        if "<YES>" in response.choices[0].message.content:
            return "YES"
        else:
            return "NO"
    except Exception:
        traceback.print_exc()
        return "ERROR"


def image_upload(filename):
    file_metadata = {
        "name": filename.split("/")[-1],
        "parents": ["1iLgEiF74QIldhAFWE2_2PfLhk2yRShW2"],
    }
    media = MediaFileUpload(filename, mimetype="image/jpeg")
    # pylint: disable=maybe-no-member
    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    return file.get("id")


def log_movement(data_ids, status):
    image_ids = [image_upload(f"log/{data_id}.jpg") for data_id in data_ids]
    image_links = [
        f"https://drive.google.com/file/d/{image_id}/view" for image_id in image_ids
    ]
    sheet.get_worksheet_by_id(0).append_row(
        [hostname, str(datetime.now()), status, *image_links]
    )


def llm_loop(queue):
    while True:
        data_ids = queue.get()

        status = detect_waste(data_ids)

        log_movement(data_ids, status)

import os
import re
import json
from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from xhtml2pdf import pisa
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "user_input": "", "json_output": ""})


@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, user_input: str = Form(...)):
    prompt = f"""
You are a report assistant for plastic bottle recycling. Given this free-form input:

\"\"\"{user_input}\"\"\"

Extract the following fields and return JSON in **this exact format**:

{{
  "party_name": "string",
  "vehicle": "string",
  "date": "DD/MM/YYYY",
  "bill_number": int,
  "bales": {{
    "bale1": {{
      "bale_weight": float,
      "tar_raffiya": float,
      "pvc": float,
      "non_pet": float,
      "non_food": float,
      "metal": float,
      "colour": float,
      "big_jar": float,
      "big_jar_mix": float,
      "d_grade": float,
      "dirty_bottle": float,
      "moisture": float
    }},
    "bale2": {{
      "bale_weight": float,
      "tar_raffiya": float,
      "pvc": float,
      "non_pet": float,
      "non_food": float,
      "metal": float,
      "colour": float,
      "big_jar": float,
      "big_jar_mix": float,
      "d_grade": float,
      "dirty_bottle": float,
      "moisture": float
    }}
  }}
}}

Only return valid JSON — no extra text, comments, or explanations.
If any value is missing, set it to 0.0.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {"role": "system", "content": "见过中文吗？我是Grok，由xAI创建。现在，让我帮你处理一些数据！"},
            {"role": "user", "content": prompt}
        ],
        "model": GROQ_MODEL,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            print("🔁 Status Code:", response.status_code)
            print("📦 Raw Text:", response.text)

            data = response.json()

            if "choices" in data:
                json_output = data["choices"][0]["message"]["content"]
            else:
                json_output = f"❌ Groq API error: {data.get('error', {}).get('message', 'Unknown error')}"
        except Exception as e:
            json_output = f"❌ Exception: {str(e)}"

    # Strip ```json wrappers
    json_output = re.sub(r"^```json\s*|```$", "", json_output.strip(), flags=re.MULTILINE).strip()

    # Parse the JSON safely
    parsed_data = None
    try:
        parsed_data = json.loads(json_output)
    except Exception as e:
        print("❌ JSON parsing failed:", str(e))
        print("⚠️ json_output was:", json_output)

    # Fallback safe access
    fallback_data = parsed_data if isinstance(parsed_data, dict) else {}

    if not parsed_data or "bales" not in parsed_data:
        parsed_data = {
            "party_name": fallback_data.get("party_name", "Unknown Party"),
            "vehicle": fallback_data.get("vehicle", "Unknown Vehicle"),
            "date": fallback_data.get("date", "01/01/2025"),
            "bill_number": fallback_data.get("bill_number", 0),
            "bales": {
                "bale1": {k: 0.0 for k in ["bale_weight", "tar_raffiya", "pvc", "non_pet", "non_food", "metal", "colour", "big_jar", "big_jar_mix", "d_grade", "dirty_bottle", "moisture"]},
                "bale2": {k: 0.0 for k in ["bale_weight", "tar_raffiya", "pvc", "non_pet", "non_food", "metal", "colour", "big_jar", "big_jar_mix", "d_grade", "dirty_bottle", "moisture"]},
            }
        }

    else:
        required_items = ["bale_weight", "tar_raffiya", "pvc", "non_pet", "non_food", "metal", "colour", "big_jar", "big_jar_mix", "d_grade", "dirty_bottle", "moisture"]
        for bale in ["bale1", "bale2"]:
            for item in required_items:
                if item not in parsed_data["bales"][bale]:
                    parsed_data["bales"][bale][item] = 0.0
            bale_weight = parsed_data["bales"][bale].get("bale_weight", 0.0)
            if bale_weight > 0:
                for item in required_items[1:]:  # Skip bale_weight
                    parsed_data["bales"][bale][f"{item}_percent"] = (parsed_data["bales"][bale].get(item, 0.0) / bale_weight) * 100

    json_output = json.dumps(parsed_data)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user_input": user_input,
        "json_output": json_output,
        "parsed_data": parsed_data
    })


@app.post("/update-json", response_class=HTMLResponse)
async def update_json(
    request: Request,
    party_name: str = Form(...),
    vehicle: str = Form(...),
    date: str = Form(...),
    bill_number: int = Form(...),
    bale1_bale_weight: float = Form(default=0.0),
    bale1_tar_raffiya: float = Form(default=0.0),
    bale1_pvc: float = Form(default=0.0),
    bale1_non_pet: float = Form(default=0.0),
    bale1_non_food: float = Form(default=0.0),
    bale1_metal: float = Form(default=0.0),
    bale1_colour: float = Form(default=0.0),
    bale1_big_jar: float = Form(default=0.0),
    bale1_big_jar_mix: float = Form(default=0.0),
    bale1_d_grade: float = Form(default=0.0),
    bale1_dirty_bottle: float = Form(default=0.0),
    bale1_moisture: float = Form(default=0.0),
    bale2_bale_weight: float = Form(default=0.0),
    bale2_tar_raffiya: float = Form(default=0.0),
    bale2_pvc: float = Form(default=0.0),
    bale2_non_pet: float = Form(default=0.0),
    bale2_non_food: float = Form(default=0.0),
    bale2_metal: float = Form(default=0.0),
    bale2_colour: float = Form(default=0.0),
    bale2_big_jar: float = Form(default=0.0),
    bale2_big_jar_mix: float = Form(default=0.0),
    bale2_d_grade: float = Form(default=0.0),
    bale2_dirty_bottle: float = Form(default=0.0),
    bale2_moisture: float = Form(default=0.0),
):
    # Construct the updated JSON
    parsed_data = {
        "party_name": party_name,
        "vehicle": vehicle,
        "date": date,
        "bill_number": bill_number,
        "bales": {
            "bale1": {
                "bale_weight": bale1_bale_weight,
                "tar_raffiya": bale1_tar_raffiya,
                "pvc": bale1_pvc,
                "non_pet": bale1_non_pet,
                "non_food": bale1_non_food,
                "metal": bale1_metal,
                "colour": bale1_colour,
                "big_jar": bale1_big_jar,
                "big_jar_mix": bale1_big_jar_mix,
                "d_grade": bale1_d_grade,
                "dirty_bottle": bale1_dirty_bottle,
                "moisture": bale1_moisture,
            },
            "bale2": {
                "bale_weight": bale2_bale_weight,
                "tar_raffiya": bale2_tar_raffiya,
                "pvc": bale2_pvc,
                "non_pet": bale2_non_pet,
                "non_food": bale2_non_food,
                "metal": bale2_metal,
                "colour": bale2_colour,
                "big_jar": bale2_big_jar,
                "big_jar_mix": bale2_big_jar_mix,
                "d_grade": bale2_d_grade,
                "dirty_bottle": bale2_dirty_bottle,
                "moisture": bale2_moisture,
            }
        }
    }

    # Calculate percentages
    required_items = ["tar_raffiya", "pvc", "non_pet", "non_food", "metal", "colour", "big_jar", "big_jar_mix", "d_grade", "dirty_bottle", "moisture"]
    for bale in ["bale1", "bale2"]:
        bale_weight = parsed_data["bales"][bale].get("bale_weight", 0.0)
        if bale_weight > 0:
            for item in required_items:
                parsed_data["bales"][bale][f"{item}_percent"] = (parsed_data["bales"][bale].get(item, 0.0) / bale_weight) * 100
        else:
            for item in required_items:
                parsed_data["bales"][bale][f"{item}_percent"] = 0.0

    json_output = json.dumps(parsed_data)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user_input": "",  # Clear the original input
        "json_output": json_output,
        "parsed_data": parsed_data
    })

@app.post("/generate-pdf")
async def generate_pdf(request: Request, report_data: str = Form(...)):
    try:
        print("📝 Raw report_data:\n", report_data)

        # Step 1: Ensure report_data is a string and parse it
        if isinstance(report_data, dict):
            raw_report = report_data
        else:
            # Remove markdown syntax if it exists
            cleaned = report_data
            if cleaned.startswith("```json"):
                cleaned = cleaned.replace("```json ", "").replace("```", "").strip()

            # Parse the JSON string
            try:
                raw_report = json.loads(cleaned)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON format: {str(e)}"}

        print("✅ Parsed dict:\n", raw_report)

        # Step 2: Validate and extract with fallback
        if not isinstance(raw_report, dict) or "bales" not in raw_report:
            return {"error": "Invalid report format. 'bales' section is missing. Please ensure the input contains bale data."}

        report = {
            "party_name": raw_report.get("party_name", "Unknown Party"),
            "vehicle": raw_report.get("vehicle", "Unknown Vehicle"),
            "date": raw_report.get("date", "01/01/2025"),
            "bill_number": raw_report.get("bill_number", 0),
            "bale1": raw_report["bales"].get("bale1", {}),
            "bale2": raw_report["bales"].get("bale2", {}),
        }

        # Step 3: Render HTML and convert to PDF
        html_content = templates.get_template("report_template.html").render(report=report)
        filename = f"report_{uuid4().hex}.pdf"
        pdf_path = f"static/{filename}"
        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html_content, dest=f)

        return FileResponse(pdf_path, media_type="application/pdf", filename="plastic_bale_report.pdf")

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
from fastapi import FastAPI, Header, HTTPException, status , Depends
from supabase import create_client, Client
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
base_id = os.getenv("BASE_ID")
table_name = "Clients response"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Login(BaseModel):
    email:str
    password:str

class Register(BaseModel):
    user_name: str
    email:str
    password:str
class Data(BaseModel):
    name:str
    number:str

def verify_token(auth: str = Header(None)):
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    try:
        token = auth.split(" ")[1]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found"
        )

    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        print("user_id:", user.user.id)
        return user.user

    except AuthApiError as e:
        # Handle expired or invalid tokens
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


url = "https://cxgobpjmqvjqtwbigkcf.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4Z29icGptcXZqcXR3Ymlna2NmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDgyMDI2OCwiZXhwIjoyMDgwMzk2MjY4fQ.XyuuJNtoothfyJcnrL3o1Giv4SSFtdQPuDvCR61FiCc"
supabase: Client = create_client(url, key)


@app.post("/login")
def login(user: Login):
    response = supabase.auth.sign_in_with_password(
        {"email": user.email, "password": user.password}
    )

    print(response)
    return response


@app.post("/register")
def register(user: Register):
    response = supabase.auth.sign_up(
        {
            "Display name": user.user_name,
            "email": user.email,
            "password": user.password,
        }
    )

    print(response)
    return response


class AirtableQuery(BaseModel):
    pageSize: int | None = None
    maxRecords: int | None = None
    offset: str | None = None
    view: str | None = None
    filterByFormula: str | None = None
    cellFormat: str | None = None
    fields: list[str] | None = None
    returnFieldsByFieldId: bool | None = None


@app.post("/airtable")
def list_records(  query: AirtableQuery  , user = Depends(verify_token)):
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    # Convert query to dict, remove None values
    params = {
        k: v
        for k, v in {
            "pageSize": 10,
            "view": "Grid view",
            "cellFormat": "string",
            "fields": ["Name", "Number", "Intent", "Date"],
        }
        .items()
        if v is not None
    }

    # Airtable requires these if cellFormat = "string"
    if params.get("cellFormat") == "string":
        params.setdefault("timeZone", "UTC")
        params.setdefault("userLocale", "en")

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    print (data)

    # Optional: Filter only the columns you want
    # if "records" in data and query.fields:
    #     for record in data["records"]:
    #         record["fields"] = {
    #             k: v for k, v in record["fields"].items() if k in query.fields
    #         }

    return data


@app.post("/airtable/save_clients")
def save_clients(client: Data):
    table_name="Clients"
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }

    # Create a new record in Airtable
    body = {
        "fields": {
            "Name": client.name,
            "Number": client.number,
        }
    }

    response = requests.post(url, json=body, headers=headers)
    data = response.json()

    print("Airtable Insert Response:", data)

    return data


@app.post("/airtable/getclients")
def list_clients_records(query: AirtableQuery):
    table_name = "Clients"

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    # Force returning only Name and Number from Airtable API
    params = {
        "pageSize": 10,
        "view": "Grid view",
        "cellFormat": "string",
        "fields[]": ["Name", "Number"],  # <--- ALWAYS request these 2 fields
        "timeZone": "UTC",
        "userLocale": "en",
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    print(data)

    # Make sure that only Name + Number are returned in every record
    if "records" in data:
        for record in data["records"]:
            fields = record.get("fields", {})
            record["fields"] = {
                "Name": fields.get("Name"),
                "Number": fields.get("Number"),
            }

    return data


# const res = await fetch("http://127.0.0.1:8000/airtable/app12345/Table1", {
#   method: "POST",
#   headers: { "Content-Type": "application/json" },
#   body: JSON.stringify({
#     pageSize: 10,
#     view: "Grid view"
#   })
# });

# const data = await res.json();
# console.log(data);


# await fetch("http://localhost:8000/airtable/save_clients", {
#   method: "POST",
#   headers: {
#     "Content-Type": "application/json",
#     auth: `Bearer ${localStorage.getItem("token")}`
#   },
#   body: JSON.stringify({
#     name: "John",
#     number: "0599..."
#   })
# })
